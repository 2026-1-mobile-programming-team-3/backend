import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import StoreCategory, StoreRequestStatus, StoreRequestType


def _validate_finite(v: float | None) -> float | None:
    if v is None:
        return v
    if not math.isfinite(v):
        raise ValueError("좌표는 유한한 수여야 합니다 (NaN/Inf 불가).")
    return v


class PricingPlanInput(BaseModel):
    """요청 payload 안의 가격 플랜 1건. PET_HOTEL 매장에만 의미.

    plan_name 중복은 서버에서 동일 매장 기준 차단(uq_store_pricing_plans_name).
    """
    plan_name: str = Field(min_length=1, max_length=100)
    price_krw: int = Field(ge=0)
    display_order: int = Field(default=0, ge=0, le=32767)


class StoreRequestPayload(BaseModel):
    """ADD/UPDATE 공용 payload. ADD는 모든 필수 필드 채워야 하고,
    UPDATE는 변경할 필드만 보내도 됨 (PATCH 시맨틱)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    category: StoreCategory | None = None
    is_pet_allowed: bool | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=20)
    operating_hours: str | None = Field(default=None, max_length=100)
    photo_urls: list[str] | None = None
    plans: list[PricingPlanInput] | None = None

    @field_validator("latitude", "longitude")
    @classmethod
    def _finite(cls, v: float | None) -> float | None:
        return _validate_finite(v)

    @model_validator(mode="after")
    def _validate_coords_paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude와 longitude는 둘 다 함께 보내야 합니다.")
        return self

    @model_validator(mode="after")
    def _validate_plan_names_unique(self):
        if self.plans:
            names = [p.plan_name for p in self.plans]
            if len(names) != len(set(names)):
                raise ValueError("plans 안에서 plan_name이 중복됩니다.")
        return self


class StoreRequestCreate(BaseModel):
    """POST /maps/store-requests body."""

    type: StoreRequestType
    target_store_id: int | None = None
    payload: StoreRequestPayload
    proof_urls: list[str] = Field(default_factory=list, max_length=10)
    message: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validate_type_target(self):
        if self.type == StoreRequestType.UPDATE and self.target_store_id is None:
            raise ValueError("UPDATE 요청은 target_store_id가 필수입니다.")
        if self.type == StoreRequestType.ADD and self.target_store_id is not None:
            raise ValueError("ADD 요청에는 target_store_id를 보내지 마세요.")
        if self.type == StoreRequestType.ADD:
            required = {
                "name": self.payload.name,
                "address": self.payload.address,
                "category": self.payload.category,
                "is_pet_allowed": self.payload.is_pet_allowed,
                "latitude": self.payload.latitude,
                "longitude": self.payload.longitude,
            }
            missing = [k for k, v in required.items() if v is None]
            if missing:
                raise ValueError(
                    f"ADD 요청 payload에 다음 필드가 필요합니다: {', '.join(missing)}"
                )
        return self


class StoreRequestCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    request_id: int = Field(alias="id")
    type: StoreRequestType
    target_store_id: int | None
    status: StoreRequestStatus
    created_at: datetime


class StoreRequestItem(BaseModel):
    """사용자 본인 목록/상세 응답."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    request_id: int = Field(alias="id")
    type: StoreRequestType
    target_store_id: int | None
    payload: dict
    proof_urls: list[str]
    message: str | None
    status: StoreRequestStatus
    review_note: str | None
    processed_at: datetime | None
    created_at: datetime


class StoreRequestListResponse(BaseModel):
    items: list[StoreRequestItem]
    total: int
    page: int
    size: int


class StoreRequestAdminItem(BaseModel):
    """관리자 목록/상세 응답. 신청자 닉네임 포함."""
    request_id: int
    user_id: int
    nickname: str | None
    type: StoreRequestType
    target_store_id: int | None
    payload: dict
    proof_urls: list[str]
    message: str | None
    status: StoreRequestStatus
    reviewer_id: int | None
    review_note: str | None
    processed_at: datetime | None
    created_at: datetime


class StoreRequestAdminListResponse(BaseModel):
    items: list[StoreRequestAdminItem]
    total: int
    page: int
    size: int


class StoreRequestActionRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    note: str | None = Field(default=None, max_length=1000)


class StoreRequestProcessedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    request_id: int = Field(alias="id")
    type: StoreRequestType
    target_store_id: int | None
    status: StoreRequestStatus
    processed_at: datetime
