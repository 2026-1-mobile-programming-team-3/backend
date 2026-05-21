import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_current_volunteer, get_db
from app.models.enums import StoreCategory
from app.models.user import User
from app.schemas.match import VolunteerLocationListResponse
from app.schemas.store import (
    PetHotelListResponse,
    StoreDetail,
    StoreFilterResponse,
    StoreNearbyResponse,
    StoreReviewCreateRequest,
    StoreReviewCreatedResponse,
    StoreReviewListResponse,
    StoreSearchResponse,
    StoreViewportQuery,
    StoreViewportResponse,
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


@router.get("/stores/viewport", response_model=StoreViewportResponse)
async def stores_in_viewport(
    sw_lat: float = Query(..., ge=-90, le=90, description="bbox 남서 위도"),
    sw_lng: float = Query(..., ge=-180, le=180, description="bbox 남서 경도"),
    ne_lat: float = Query(..., ge=-90, le=90, description="bbox 북동 위도"),
    ne_lng: float = Query(..., ge=-180, le=180, description="bbox 북동 경도"),
    category: StoreCategory | None = Query(None, description="카테고리 필터 (옵션)"),
    db: AsyncSession = Depends(get_db),
):
    try:
        q = StoreViewportQuery(
            sw_lat=sw_lat, sw_lng=sw_lng, ne_lat=ne_lat, ne_lng=ne_lng
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return await store_service.viewport_stores(
        db,
        sw_lat=q.sw_lat,
        sw_lng=q.sw_lng,
        ne_lat=q.ne_lat,
        ne_lng=q.ne_lng,
        category=category,
    )


@router.get("/stores", response_model=StoreNearbyResponse)
async def nearby_stores(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lng: float = Query(..., ge=-180, le=180, description="경도"),
    radius: int = Query(2000, ge=1, le=50_000, description="반경 (m), 최대 50km"),
    db: AsyncSession = Depends(get_db),
):
    return await store_service.nearby_stores(db, lat, lng, radius)


_GONE_DETAIL = (
    "이 엔드포인트는 폐기되었습니다. POST /maps/store-requests 로 추가/수정 요청을 제출하세요."
)


@router.post("/stores", deprecated=True, include_in_schema=True)
async def create_store_gone():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_GONE_DETAIL)


@router.get("/pet-hotels", response_model=PetHotelListResponse)
async def list_pet_hotels(
    lat: float = Query(..., ge=-90, le=90, description="기준 위도"),
    lng: float = Query(..., ge=-180, le=180, description="기준 경도"),
    radius: int = Query(
        5000, ge=1, le=50_000, description="검색 반경 (m), 최대 50km"
    ),
    db: AsyncSession = Depends(get_db),
):
    if not (math.isfinite(lat) and math.isfinite(lng)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lat/lng는 유한한 수여야 합니다.",
        )
    return await store_service.list_pet_hotels(db, lat, lng, radius)


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


@router.put("/stores/{store_id}", deprecated=True, include_in_schema=True)
async def update_store_gone(store_id: int):
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_GONE_DETAIL)


@router.delete("/stores/{store_id}", deprecated=True, include_in_schema=True)
async def delete_store_gone(store_id: int):
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_GONE_DETAIL)


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
