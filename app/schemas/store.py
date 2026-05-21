import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import StoreCategory


def _validate_finite(v: float | None) -> float | None:
    if v is None:
        return v
    if not math.isfinite(v):
        raise ValueError("좌표는 유한한 수여야 합니다 (NaN/Inf 불가).")
    return v


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


class PricingPlanItem(BaseModel):
    """PET_HOTEL 매장의 가격 플랜 1건. plan_name은 자유 텍스트로 단위 포함 가능 ('1박 소형견').

    다른 카테고리 매장에서는 plans가 항상 빈 배열로 응답된다.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    plan_name: str
    price_krw: int
    display_order: int = 0


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
    category: StoreCategory
    rating_avg: float
    review_pet_allowed_rate: float
    is_favorited: bool = False
    plans: list[PricingPlanItem] = Field(default_factory=list)


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
    thumbnail_url: str | None = None
    rating_avg: float | None = None
    is_favorited: bool = False
    distance_m: float


class StoreNearbyResponse(BaseModel):
    stores: list[StoreNearbyItem]


class StoreViewportItem(BaseModel):
    """지도 viewport 응답 항목 — 거리 없음, 마커 렌더에 필요한 최소 정보."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    store_id: int = Field(alias="id")
    name: str
    latitude: float
    longitude: float
    category: StoreCategory
    is_pet_allowed: bool
    rating_avg: float | None = None
    rating_count: int = 0


class StoreViewportResponse(BaseModel):
    stores: list[StoreViewportItem]
    truncated: bool = Field(
        default=False,
        description="결과가 limit(=200)에 잘려서 일부만 반환된 경우 true. 클라이언트가 줌인 안내를 띄울 수 있다.",
    )


class StoreViewportQuery(BaseModel):
    """bbox 좌표 페어 유효성 검증용 내부 모델."""
    sw_lat: float = Field(ge=-90, le=90)
    sw_lng: float = Field(ge=-180, le=180)
    ne_lat: float = Field(ge=-90, le=90)
    ne_lng: float = Field(ge=-180, le=180)

    @field_validator("sw_lat", "sw_lng", "ne_lat", "ne_lng")
    @classmethod
    def _finite(cls, v: float) -> float:
        return _validate_finite(v)  # type: ignore[return-value]

    @model_validator(mode="after")
    def _validate_box(self):
        if self.sw_lat >= self.ne_lat:
            raise ValueError("sw_lat은 ne_lat보다 작아야 합니다.")
        if self.sw_lng >= self.ne_lng:
            raise ValueError(
                "sw_lng은 ne_lng보다 작아야 합니다. (날짜변경선을 가로지르는 박스는 지원하지 않음 — 한국 서비스이므로 발생할 일 없음.)"
            )
        return self


class StoreReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    is_pet_allowed: bool
    content: str = Field(min_length=1, max_length=2000)


class StoreReviewCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    review_id: int = Field(alias="id")
    rating: int
    is_pet_allowed: bool
    content: str
    created_at: datetime


class PetHotelItem(BaseModel):
    """GET /maps/pet-hotels 의 매장 1건. 플랜 + 가격 요약 포함."""

    store_id: int
    name: str
    address: str
    latitude: float
    longitude: float
    distance_m: float
    is_pet_allowed: bool
    thumbnail_url: str | None = None
    rating_avg: float | None = None
    rating_count: int = 0
    plan_count: int
    min_price_krw: int | None = None
    max_price_krw: int | None = None
    plans: list[PricingPlanItem] = Field(default_factory=list)


class PetHotelListResponse(BaseModel):
    pet_hotels: list[PetHotelItem]
