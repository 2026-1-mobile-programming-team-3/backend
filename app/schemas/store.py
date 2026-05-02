from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StoreCategory


class StoreSummary(BaseModel):
    """5.5 필터 응답용 (좌표 포함, address 없음)"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    store_id: int = Field(alias="id")
    name: str
    latitude: float
    longitude: float
    category: StoreCategory
    is_pet_allowed: bool


class StoreSearchItem(BaseModel):
    """5.4 검색 응답 — 좌표 없는 가벼운 형태 (명세 일치)"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    store_id: int = Field(alias="id")
    name: str
    address: str
    category: StoreCategory


class StoreDetail(BaseModel):
    """5.3 상세"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    store_id: int = Field(alias="id")
    name: str
    address: str
    phone: str | None
    operating_hours: str | None
    photo_urls: list[str]
    is_pet_allowed: bool
    rating_avg: float
    review_pet_allowed_rate: float


class StoreFilterResponse(BaseModel):
    stores: list[StoreSummary]


class StoreSearchResponse(BaseModel):
    results: list[StoreSearchItem]


class StoreReviewItem(BaseModel):
    """5.9"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    review_id: int = Field(alias="id")
    nickname: str
    rating: int
    is_pet_allowed: bool
    content: str
    created_at: datetime


class StoreReviewListResponse(BaseModel):
    reviews: list[StoreReviewItem]


class StoreNearbyItem(BaseModel):
    """5.1 반경 응답 항목 (좌표 + 거리 포함)"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    store_id: int = Field(alias="id")
    name: str
    latitude: float
    longitude: float
    category: StoreCategory
    is_pet_allowed: bool
    distance_m: float


class StoreNearbyResponse(BaseModel):
    stores: list[StoreNearbyItem]
