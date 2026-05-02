from geoalchemy2 import Geography, Geometry
from sqlalchemy import func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.enums import StoreCategory, StoreStatus
from app.models.store import Store, StoreReview
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
    """name ILIKE 또는 address ILIKE 매칭. 결과 50개 cap."""
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
    """좌표 포함 (Store, lat, lng) 튜플 리스트. 결과 200개 cap."""
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
