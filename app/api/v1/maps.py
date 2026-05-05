from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_current_volunteer, get_db
from app.models.enums import StoreCategory
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.match import VolunteerLocationListResponse
from app.schemas.store import (
    StoreCreateRequest,
    StoreCreateResponse,
    StoreDetail,
    StoreFilterResponse,
    StoreNearbyResponse,
    StoreReviewCreateRequest,
    StoreReviewCreatedResponse,
    StoreReviewListResponse,
    StoreSearchResponse,
    StoreUpdateRequest,
)
from app.services import match as match_service
from app.services import store as store_service

router = APIRouter(prefix="/maps", tags=["Maps"])


# /stores/search 와 /stores/filter 가 /stores/{store_id} 보다 먼저 등록되어야
# FastAPI가 path 충돌을 일으키지 않는다.
@router.get("/stores/search", response_model=StoreSearchResponse)
async def search_stores(
    keyword: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    return await store_service.search_stores(db, keyword)


@router.get("/stores/filter", response_model=StoreFilterResponse)
async def filter_stores(
    category: StoreCategory | None = Query(None),
    is_pet_allowed: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await store_service.filter_stores(db, category, is_pet_allowed)


@router.get("/stores", response_model=StoreNearbyResponse)
async def nearby_stores(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lng: float = Query(..., ge=-180, le=180, description="경도"),
    radius: int = Query(2000, ge=1, le=50_000, description="반경 (m), 최대 50km"),
    db: AsyncSession = Depends(get_db),
):
    return await store_service.nearby_stores(db, lat, lng, radius)


@router.post(
    "/stores",
    response_model=StoreCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_store(
    data: StoreCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_service.create_store(
        db, current_user_id=current_user.id, data=data
    )


@router.get("/volunteers", response_model=VolunteerLocationListResponse)
async def list_volunteer_locations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_volunteer),
):
    return await match_service.list_volunteer_locations(db, current_user=current_user)


@router.get("/stores/{store_id}", response_model=StoreDetail)
async def get_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await store_service.get_store_detail(db, store_id)


@router.put("/stores/{store_id}", response_model=MessageResponse)
async def update_store(
    store_id: int,
    data: StoreUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_service.update_store(
        db, current_user=current_user, store_id=store_id, data=data
    )


@router.delete("/stores/{store_id}", response_model=MessageResponse)
async def delete_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_service.delete_store(
        db, current_user=current_user, store_id=store_id
    )


@router.get("/stores/{store_id}/reviews", response_model=StoreReviewListResponse)
async def get_store_reviews(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await store_service.list_store_reviews(db, store_id)


@router.post(
    "/stores/{store_id}/reviews",
    response_model=StoreReviewCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    store_id: int,
    data: StoreReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_service.create_review(
        db, current_user_id=current_user.id, store_id=store_id, data=data
    )


@router.delete(
    "/stores/{store_id}/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_review(
    store_id: int,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await store_service.delete_review(
        db,
        current_user_id=current_user.id,
        store_id=store_id,
        review_id=review_id,
    )
