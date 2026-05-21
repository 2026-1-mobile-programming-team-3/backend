from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import store as store_crud
from app.models.enums import StoreCategory
from app.schemas.store import (
    PetHotelItem,
    PetHotelListResponse,
    PricingPlanItem,
    StoreDetail,
    StoreFilterResponse,
    StoreNearbyItem,
    StoreNearbyResponse,
    StoreReviewCreateRequest,
    StoreReviewCreatedResponse,
    StoreReviewItem,
    StoreReviewListResponse,
    StoreSearchItem,
    StoreSearchResponse,
    StoreSummary,
    StoreViewportItem,
    StoreViewportResponse,
)

_DELETED_USER_NICKNAME = "(탈퇴한 사용자)"


async def get_store_detail(db: AsyncSession, store_id: int) -> StoreDetail:
    store = await store_crud.get_approved_by_id(db, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    pet_rate = await store_crud.review_pet_allowed_rate(db, store_id)
    plans: list[PricingPlanItem] = []
    if store.category == StoreCategory.PET_HOTEL:
        plan_rows = await store_crud.list_plans_for_store(db, store_id)
        plans = [
            PricingPlanItem(
                plan_name=p.plan_name,
                price_krw=p.price_krw,
                display_order=p.display_order,
            )
            for p in plan_rows
        ]
    return StoreDetail(
        store_id=store.id,
        name=store.name,
        address=store.address,
        phone=store.phone,
        operating_hours=store.operating_hours,
        photo_urls=list(store.photo_urls or []),
        is_pet_allowed=store.is_pet_allowed,
        category=store.category,
        rating_avg=float(store.rating_avg),
        review_pet_allowed_rate=pet_rate,
        is_favorited=False,
        plans=plans,
    )


async def list_pet_hotels(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_m: int,
) -> PetHotelListResponse:
    rows = await store_crud.nearby_pet_hotels(db, lat, lng, radius_m)
    store_ids = [s.id for s, *_ in rows]
    plans_by_store = await store_crud.list_plans_for_stores(db, store_ids)

    items: list[PetHotelItem] = []
    for store, row_lat, row_lng, distance_m in rows:
        plans = plans_by_store.get(store.id, [])
        prices = [p.price_krw for p in plans]
        items.append(
            PetHotelItem(
                store_id=store.id,
                name=store.name,
                address=store.address,
                latitude=row_lat,
                longitude=row_lng,
                distance_m=round(distance_m, 1),
                is_pet_allowed=store.is_pet_allowed,
                thumbnail_url=(store.photo_urls[0] if store.photo_urls else None),
                rating_avg=(
                    round(float(store.rating_avg), 1)
                    if store.rating_count > 0
                    else None
                ),
                rating_count=store.rating_count,
                plan_count=len(plans),
                min_price_krw=min(prices) if prices else None,
                max_price_krw=max(prices) if prices else None,
                plans=[
                    PricingPlanItem(
                        plan_name=p.plan_name,
                        price_krw=p.price_krw,
                        display_order=p.display_order,
                    )
                    for p in plans
                ],
            )
        )
    return PetHotelListResponse(pet_hotels=items)


async def search_stores(db: AsyncSession, keyword: str) -> StoreSearchResponse:
    stores = await store_crud.search_approved(db, keyword)
    return StoreSearchResponse(
        results=[
            StoreSearchItem(
                store_id=s.id,
                name=s.name,
                address=s.address,
                category=s.category,
            )
            for s in stores
        ]
    )


async def filter_stores(
    db: AsyncSession,
    category: StoreCategory | None,
    is_pet_allowed: bool | None,
) -> StoreFilterResponse:
    rows = await store_crud.filter_approved(db, category, is_pet_allowed)
    return StoreFilterResponse(
        stores=[
            StoreSummary(
                store_id=s.id,
                name=s.name,
                latitude=lat,
                longitude=lng,
                category=s.category,
                is_pet_allowed=s.is_pet_allowed,
            )
            for s, lat, lng in rows
        ]
    )


async def viewport_stores(
    db: AsyncSession,
    *,
    sw_lat: float,
    sw_lng: float,
    ne_lat: float,
    ne_lng: float,
    category: StoreCategory | None,
) -> StoreViewportResponse:
    rows, truncated = await store_crud.list_within_viewport(
        db,
        sw_lat=sw_lat,
        sw_lng=sw_lng,
        ne_lat=ne_lat,
        ne_lng=ne_lng,
        category=category,
    )
    return StoreViewportResponse(
        stores=[
            StoreViewportItem(
                store_id=s.id,
                name=s.name,
                latitude=lat,
                longitude=lng,
                category=s.category,
                is_pet_allowed=s.is_pet_allowed,
                rating_avg=(round(float(s.rating_avg), 1) if s.rating_count > 0 else None),
                rating_count=s.rating_count,
            )
            for s, lat, lng in rows
        ],
        truncated=truncated,
    )


async def nearby_stores(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_m: int,
) -> StoreNearbyResponse:
    rows = await store_crud.nearby_approved(db, lat, lng, radius_m)
    return StoreNearbyResponse(
        stores=[
            StoreNearbyItem(
                store_id=s.id,
                name=s.name,
                latitude=row_lat,
                longitude=row_lng,
                category=s.category,
                is_pet_allowed=s.is_pet_allowed,
                thumbnail_url=(s.photo_urls[0] if s.photo_urls else None),
                rating_avg=(round(float(s.rating_avg), 1) if s.rating_count > 0 else None),
                is_favorited=False,
                distance_m=round(distance_m, 1),
            )
            for s, row_lat, row_lng, distance_m in rows
        ]
    )


async def list_store_reviews(
    db: AsyncSession, store_id: int
) -> StoreReviewListResponse:
    store = await store_crud.get_approved_by_id(db, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    rows = await store_crud.list_reviews_with_authors(db, store_id)
    return StoreReviewListResponse(
        reviews=[
            StoreReviewItem(
                review_id=review.id,
                nickname=nickname if nickname is not None else _DELETED_USER_NICKNAME,
                rating=review.rating,
                is_pet_allowed=review.is_pet_allowed,
                content=review.content,
                created_at=review.created_at,
            )
            for review, nickname in rows
        ]
    )


async def create_review(
    db: AsyncSession,
    *,
    current_user_id: int,
    store_id: int,
    data: StoreReviewCreateRequest,
) -> StoreReviewCreatedResponse:
    store = await store_crud.get_approved_by_id(db, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    try:
        review = await store_crud.create_review(
            db,
            store_id=store_id,
            author_id=current_user_id,
            rating=data.rating,
            is_pet_allowed=data.is_pet_allowed,
            content=data.content,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 이 매장에 리뷰를 작성했습니다.",
        )
    return StoreReviewCreatedResponse(
        id=review.id,
        rating=review.rating,
        is_pet_allowed=review.is_pet_allowed,
        content=review.content,
        created_at=review.created_at,
    )


async def delete_review(
    db: AsyncSession,
    *,
    current_user_id: int,
    store_id: int,
    review_id: int,
) -> None:
    review = await store_crud.get_review(db, review_id)
    if review is None or review.store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 리뷰를 찾을 수 없습니다.",
        )
    if review.author_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 작성한 리뷰만 삭제할 수 있습니다.",
        )
    await store_crud.delete_review(db, review)
    await db.commit()
