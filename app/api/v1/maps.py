from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.enums import StoreCategory
from app.schemas.store import (
    StoreDetail,
    StoreFilterResponse,
    StoreNearbyResponse,
    StoreReviewListResponse,
    StoreSearchResponse,
)
from app.services import store as store_service

router = APIRouter(prefix="/maps", tags=["Maps"])


# /stores/search 와 /stores/filter 가 /stores/{store_id} 보다 먼저 등록되어야
# FastAPI가 path 충돌을 일으키지 않는다.
@router.get("/stores/search", response_model=StoreSearchResponse)
async def search_stores(
    keyword: str = Query(..., min_length=1),
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


@router.get("/stores/{store_id}", response_model=StoreDetail)
async def get_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await store_service.get_store_detail(db, store_id)


@router.get("/stores/{store_id}/reviews", response_model=StoreReviewListResponse)
async def get_store_reviews(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await store_service.list_store_reviews(db, store_id)
