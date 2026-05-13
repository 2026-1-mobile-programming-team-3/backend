from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_password_strength, validate_phone
from app.models.enums import PetGender, PetSpecies, UserRole, VolunteerBadgeTier


class PetSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    species: PetSpecies
    breed: str | None
    age: int | None
    gender: PetGender
    is_neutered: bool


class UserMeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    nickname: str
    phone: str | None
    role: UserRole
    profile_image_url: str | None
    region_si: str | None
    region_dong: str | None
    pets: list[PetSummary] = []
    created_at: datetime


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    nickname: str
    phone: str | None
    role: UserRole
    profile_image_url: str | None
    region_si: str | None
    region_dong: str | None
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    phone: str | None = None
    profile_image_url: str | None = None
    region_si: str | None = None
    region_dong: str | None = None

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not (2 <= len(v) <= 20):
            raise ValueError("닉네임은 2자 이상 20자 이하여야 합니다.")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return validate_phone(v)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class AccountDeleteRequest(BaseModel):
    password: str
    reason: str | None = Field(default=None, max_length=500)


class VolunteerRequestCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class VolunteerRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    message: str
    status: str
    created_at: datetime


# ─── 마이페이지: 활동 통계 + 봉사 뱃지 ────────────────────────────────────────


class VolunteerBadgeInfo(BaseModel):
    """봉사 뱃지 등급 정보.
    임계값: SEED 1 / FLOWER 3 / FRUIT 8 / TREE 15."""

    tier: VolunteerBadgeTier
    count: int
    next_tier: VolunteerBadgeTier | None
    next_threshold: int | None
    progress_pct: int  # 0~100 (현 등급 시작 ~ 다음 등급 임계)


class ActivityStatsResponse(BaseModel):
    my_match_count: int
    volunteer_completed_count: int
    favorite_count: int
    badge: VolunteerBadgeInfo
