from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import store as store_crud
from app.models.enums import StoreCategory, UserRole
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.store import (
    StoreCreateRequest,
    StoreCreateResponse,
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
    StoreUpdateRequest,
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
        is_favorited=False,
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


async def create_store(
    db: AsyncSession,
    *,
    current_user_id: int,
    data: StoreCreateRequest,
) -> StoreCreateResponse:
    store = await store_crud.create_store(
        db,
        name=data.name,
        address=data.address,
        phone=data.phone,
        category=data.category,
        lat=data.latitude,
        lng=data.longitude,
        operating_hours=data.operating_hours,
        photo_urls=data.photo_urls,
        is_pet_allowed=data.is_pet_allowed,
        created_by=current_user_id,
    )
    return StoreCreateResponse(store_id=store.id, status=store.status)


async def update_store(
    db: AsyncSession,
    *,
    current_user: User,
    store_id: int,
    data: StoreUpdateRequest,
) -> MessageResponse:
    store = await store_crud.get_by_id_for_owner(db, store_id)
    if store is None or store.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    if store.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 등록한 매장만 수정할 수 있습니다.",
        )
    fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if not fields:
        return MessageResponse(message="변경 사항 없음")
    await store_crud.update_store(db, store, **fields)
    await db.commit()
    return MessageResponse(message="성공적으로 처리되었습니다.")


async def delete_store(
    db: AsyncSession,
    *,
    current_user: User,
    store_id: int,
) -> MessageResponse:
    store = await store_crud.get_by_id_for_owner(db, store_id)
    if store is None or store.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    if store.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 등록한 매장만 삭제할 수 있습니다.",
        )
    await store_crud.soft_delete_store(db, store)
    await db.commit()
    return MessageResponse(message="성공적으로 처리되었습니다.")


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
