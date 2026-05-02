from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import StoreCategory, StoreStatus


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


class StoreCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    category: StoreCategory
    is_pet_allowed: bool
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=20)
    operating_hours: str | None = Field(default=None, max_length=100)
    photo_urls: list[str] = Field(default_factory=list)


class StoreCreateResponse(BaseModel):
    store_id: int
    status: StoreStatus


class StoreUpdateRequest(BaseModel):
    """전송된 필드만 갱신 (사실상 PATCH 시맨틱). 모든 필드 옵션."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    category: StoreCategory | None = None
    is_pet_allowed: bool | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=20)
    operating_hours: str | None = Field(default=None, max_length=100)
    photo_urls: list[str] | None = None

    @model_validator(mode="after")
    def validate_coords_paired(self):
        """lat/lng는 둘 다 있거나 둘 다 없어야 함 — 한쪽만 변경은 의미 없음."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude와 longitude는 둘 다 함께 보내야 합니다.")
        return self


class StoreReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    is_pet_allowed: bool
    content: str = Field(min_length=1)


class StoreReviewCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    review_id: int = Field(alias="id")
    rating: int
    is_pet_allowed: bool
    content: str
    created_at: datetime
