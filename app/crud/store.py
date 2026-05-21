from geoalchemy2 import Geography, Geometry
from sqlalchemy import func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.enums import StoreCategory, StoreStatus
from app.models.store import Store, StorePricingPlan, StoreReview
from app.models.user import User


async def get_approved_by_id(db: AsyncSession, store_id: int) -> Store | None:
    """status=APPROVED AND deleted_at IS NULL 매장만 조회."""
    stmt = select(Store).where(
        Store.id == store_id,
        Store.status == StoreStatus.APPROVED,
        Store.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def search_approved(db: AsyncSession, keyword: str) -> list[Store]:
    """name ILIKE 또는 address ILIKE 매칭. 검색은 텍스트 결과 리스트라 50개로 캡 (가독성)."""
    pattern = f"%{keyword}%"
    stmt = (
        select(Store)
        .where(
            Store.status == StoreStatus.APPROVED,
            Store.deleted_at.is_(None),
            or_(
                Store.name.ilike(pattern),
                Store.address.ilike(pattern),
            ),
        )
        .order_by(Store.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def filter_approved(
    db: AsyncSession,
    category: StoreCategory | None,
    is_pet_allowed: bool | None,
) -> list[tuple[Store, float, float]]:
    """좌표 포함 (Store, lat, lng) 튜플 리스트. 지도 마커 표시용이라 200개로 캡 (검색 50과 의도적 차등)."""
    location_geom = func.cast(Store.location, Geometry)
    stmt = select(
        Store,
        func.ST_Y(location_geom).label("lat"),
        func.ST_X(location_geom).label("lng"),
    ).where(
        Store.status == StoreStatus.APPROVED,
        Store.deleted_at.is_(None),
    )
    if category is not None:
        stmt = stmt.where(Store.category == category)
    if is_pet_allowed is not None:
        stmt = stmt.where(Store.is_pet_allowed == is_pet_allowed)
    stmt = stmt.order_by(Store.created_at.desc()).limit(200)

    result = await db.execute(stmt)
    return [(row[0], float(row[1]), float(row[2])) for row in result.all()]


async def nearby_approved(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_m: int,
) -> list[tuple[Store, float, float, float]]:
    """
    반경 내 APPROVED 매장 (Store, lat, lng, distance_m) 튜플 리스트.
    거리 오름차순, 결과 200개 cap.
    """
    point = func.cast(
        func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326),
        Geography,
    )
    location_geom = func.cast(Store.location, Geometry)
    distance_expr = func.ST_Distance(Store.location, point).label("distance_m")

    stmt = (
        select(
            Store,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
            distance_expr,
        )
        .where(
            Store.status == StoreStatus.APPROVED,
            Store.deleted_at.is_(None),
            func.ST_DWithin(Store.location, point, radius_m),
        )
        .order_by(distance_expr.asc())
        .limit(200)
    )
    result = await db.execute(stmt)
    return [
        (row[0], float(row[1]), float(row[2]), float(row[3]))
        for row in result.all()
    ]


VIEWPORT_LIMIT = 200


async def list_within_viewport(
    db: AsyncSession,
    *,
    sw_lat: float,
    sw_lng: float,
    ne_lat: float,
    ne_lng: float,
    category: StoreCategory | None,
) -> tuple[list[tuple[Store, float, float]], bool]:
    """
    bbox(viewport) 안 APPROVED 매장 (Store, lat, lng) + truncated 플래그.
    ST_MakeEnvelope 로 박스를 만들고, 같은 GiST 인덱스를 그대로 활용 (idx_stores_location_gist).
    """
    envelope = func.ST_MakeEnvelope(sw_lng, sw_lat, ne_lng, ne_lat, 4326)
    location_geom = func.cast(Store.location, Geometry)
    stmt = (
        select(
            Store,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
        )
        .where(
            Store.status == StoreStatus.APPROVED,
            Store.deleted_at.is_(None),
            func.ST_Intersects(location_geom, envelope),
        )
    )
    if category is not None:
        stmt = stmt.where(Store.category == category)
    stmt = stmt.order_by(Store.id.asc()).limit(VIEWPORT_LIMIT + 1)
    result = await db.execute(stmt)
    rows = [(row[0], float(row[1]), float(row[2])) for row in result.all()]
    truncated = len(rows) > VIEWPORT_LIMIT
    return rows[:VIEWPORT_LIMIT], truncated


async def list_reviews_with_authors(
    db: AsyncSession, store_id: int
) -> list[tuple[StoreReview, str | None]]:
    """(review, nickname) 튜플 리스트. user 탈퇴/미존재 시 nickname=None."""
    stmt = (
        select(StoreReview, User.nickname)
        .outerjoin(
            User,
            (User.id == StoreReview.author_id) & (User.deleted_at.is_(None)),
        )
        .where(StoreReview.store_id == store_id)
        .order_by(StoreReview.created_at.desc())
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def review_pet_allowed_rate(db: AsyncSession, store_id: int) -> float:
    """리뷰 중 is_pet_allowed=true 비율. 0건이면 0.0."""
    stmt = text(
        """
        SELECT COALESCE(AVG(CASE WHEN is_pet_allowed THEN 1.0 ELSE 0.0 END), 0)::float
        FROM store_reviews
        WHERE store_id = :store_id
        """
    )
    result = await db.execute(stmt, {"store_id": store_id})
    value = result.scalar_one()
    return float(value) if value is not None else 0.0


async def get_by_id_for_owner(db: AsyncSession, store_id: int) -> Store | None:
    """deleted_at·status 무관, 단순 PK 조회. 소유자 검증은 호출자 책임."""
    stmt = select(Store).where(Store.id == store_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_review(
    db: AsyncSession,
    *,
    store_id: int,
    author_id: int,
    rating: int,
    is_pet_allowed: bool,
    content: str,
) -> StoreReview:
    """unique(store_id, author_id) 위반 시 IntegrityError 발생 — 호출자가 잡아 409 변환."""
    review = StoreReview(
        store_id=store_id,
        author_id=author_id,
        rating=rating,
        is_pet_allowed=is_pet_allowed,
        content=content,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review(db: AsyncSession, review_id: int) -> StoreReview | None:
    stmt = select(StoreReview).where(StoreReview.id == review_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_review(db: AsyncSession, review: StoreReview) -> None:
    """commit은 호출자 책임."""
    await db.delete(review)


# ─── Pricing plans (PET_HOTEL) ──────────────────────────────────────────────

async def list_plans_for_store(
    db: AsyncSession, store_id: int
) -> list[StorePricingPlan]:
    stmt = (
        select(StorePricingPlan)
        .where(StorePricingPlan.store_id == store_id)
        .order_by(StorePricingPlan.display_order.asc(), StorePricingPlan.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_plans_for_stores(
    db: AsyncSession, store_ids: list[int]
) -> dict[int, list[StorePricingPlan]]:
    """매장 N개에 대한 plans 일괄 조회 → {store_id: [plan, ...]} 매핑.
    빈 매장은 키 자체가 없음."""
    if not store_ids:
        return {}
    stmt = (
        select(StorePricingPlan)
        .where(StorePricingPlan.store_id.in_(store_ids))
        .order_by(StorePricingPlan.store_id.asc(), StorePricingPlan.display_order.asc())
    )
    result = await db.execute(stmt)
    grouped: dict[int, list[StorePricingPlan]] = {}
    for plan in result.scalars().all():
        grouped.setdefault(plan.store_id, []).append(plan)
    return grouped


async def replace_plans(
    db: AsyncSession, store_id: int, plans_payload: list[dict]
) -> list[StorePricingPlan]:
    """매장의 plans를 통째로 교체 (replace-all 시맨틱). commit은 호출자.

    plans_payload는 [{plan_name, price_krw, display_order?}, ...] 형태."""
    # 기존 plans 모두 삭제
    await db.execute(
        text("DELETE FROM store_pricing_plans WHERE store_id = :sid"),
        {"sid": store_id},
    )
    created: list[StorePricingPlan] = []
    for idx, p in enumerate(plans_payload):
        plan = StorePricingPlan(
            store_id=store_id,
            plan_name=p["plan_name"],
            price_krw=p["price_krw"],
            display_order=p.get("display_order", idx),
        )
        db.add(plan)
        created.append(plan)
    return created


async def nearby_pet_hotels(
    db: AsyncSession, lat: float, lng: float, radius_m: int, limit: int = 50
) -> list[tuple[Store, float, float, float]]:
    """반경 내 APPROVED + category=PET_HOTEL 매장 (Store, lat, lng, distance_m).
    거리 오름차순, limit cap."""
    point = func.cast(
        func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326),
        Geography,
    )
    location_geom = func.cast(Store.location, Geometry)
    distance_expr = func.ST_Distance(Store.location, point).label("distance_m")
    stmt = (
        select(
            Store,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
            distance_expr,
        )
        .where(
            Store.status == StoreStatus.APPROVED,
            Store.deleted_at.is_(None),
            Store.category == StoreCategory.PET_HOTEL,
            func.ST_DWithin(Store.location, point, radius_m),
        )
        .order_by(distance_expr.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        (row[0], float(row[1]), float(row[2]), float(row[3]))
        for row in result.all()
    ]


async def insert_store_from_payload(
    db: AsyncSession,
    *,
    payload: dict,
    owner_user_id: int,
) -> Store:
    """store_requests ADD 승인 시 호출. status=APPROVED 즉시. commit은 호출자."""
    store = Store(
        name=payload["name"],
        address=payload["address"],
        phone=payload.get("phone"),
        category=StoreCategory(payload["category"]),
        location=func.ST_SetSRID(
            func.ST_MakePoint(payload["longitude"], payload["latitude"]),
            4326,
        ).cast(Geography),
        operating_hours=payload.get("operating_hours"),
        photo_urls=payload.get("photo_urls") or [],
        is_pet_allowed=bool(payload["is_pet_allowed"]),
        status=StoreStatus.APPROVED,
        created_by=owner_user_id,
        owner_user_id=owner_user_id,
    )
    db.add(store)
    await db.flush()
    return store


async def apply_update_payload(
    db: AsyncSession, store: Store, payload: dict
) -> Store:
    """UPDATE 요청 승인 시 호출. payload에 있는 키만 갱신. commit은 호출자."""
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    simple_keys = (
        "name",
        "address",
        "category",
        "is_pet_allowed",
        "phone",
        "operating_hours",
        "photo_urls",
    )
    for key in simple_keys:
        if key in payload and payload[key] is not None:
            value = payload[key]
            if key == "category":
                value = StoreCategory(value)
            setattr(store, key, value)
    if lat is not None and lng is not None:
        store.location = func.ST_SetSRID(
            func.ST_MakePoint(lng, lat), 4326
        ).cast(Geography)
    return store
