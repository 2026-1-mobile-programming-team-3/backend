from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import store as store_crud
from app.models.enums import StoreCategory
from app.schemas.store import (
    StoreDetail,
    StoreFilterResponse,
    StoreNearbyItem,
    StoreNearbyResponse,
    StoreReviewItem,
    StoreReviewListResponse,
    StoreSearchItem,
    StoreSearchResponse,
    StoreSummary,
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
    return StoreDetail(
        store_id=store.id,
        name=store.name,
        address=store.address,
        phone=store.phone,
        operating_hours=store.operating_hours,
        photo_urls=list(store.photo_urls or []),
        is_pet_allowed=store.is_pet_allowed,
        rating_avg=float(store.rating_avg),
        review_pet_allowed_rate=pet_rate,
    )


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
