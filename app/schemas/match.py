import math
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ApplicationStatus, MatchStatus, PetSpecies


def _validate_finite(v: float | None) -> float | None:
    if v is None:
        return v
    if not math.isfinite(v):
        raise ValueError("좌표는 유한한 수여야 합니다 (NaN/Inf 불가).")
    return v


# ─── /maps/volunteers ────────────────────────────────────────────────────────


class VolunteerLocationItem(BaseModel):
    request_id: int
    title: str
    latitude: float
    longitude: float
    status: MatchStatus


class VolunteerLocationListResponse(BaseModel):
    volunteer_requests: list[VolunteerLocationItem]


# ─── 3.1 POST /matches ───────────────────────────────────────────────────────


class MatchCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=10_000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=255)
    desired_date: date | None = None
    pet_id: int | None = None

    @field_validator("latitude", "longitude")
    @classmethod
    def _finite(cls, v: float) -> float:
        return _validate_finite(v)  # type: ignore[return-value]


class MatchCreatedResponse(BaseModel):
    match_id: int
    status: MatchStatus
    created_at: datetime


# ─── 3.4 GET /matches ────────────────────────────────────────────────────────


class MatchListItem(BaseModel):
    match_id: int
    title: str
    address: str | None
    latitude: float
    longitude: float
    desired_date: date | None
    status: MatchStatus
    author_nickname: str | None
    created_at: datetime


class MatchListResponse(BaseModel):
    items: list[MatchListItem]
    total: int
    page: int
    size: int


# ─── 3.5 GET /matches/{match_id} ─────────────────────────────────────────────


class MatchAuthorSummary(BaseModel):
    user_id: int
    nickname: str | None


class MatchPetSummary(BaseModel):
    pet_id: int
    name: str
    species: PetSpecies
    is_neutered: bool


class MatchDetail(BaseModel):
    match_id: int
    author: MatchAuthorSummary
    pet: MatchPetSummary | None
    title: str
    content: str
    address: str | None
    latitude: float
    longitude: float
    desired_date: date | None
    status: MatchStatus
    applications_count: int
    created_at: datetime


# ─── 3.6 POST /matches/{match_id}/applications ───────────────────────────────


class ApplicationCreateRequest(BaseModel):
    message: str | None = Field(default=None, max_length=2000)


class ApplicationCreatedResponse(BaseModel):
    application_id: int
    match_id: int
    applicant_id: int
    status: ApplicationStatus
    created_at: datetime


# ─── 3.7 GET /matches/{match_id}/applications ────────────────────────────────


class ApplicationApplicantInfo(BaseModel):
    applicant_id: int
    nickname: str | None


class ApplicationListItem(BaseModel):
    application_id: int
    applicant: ApplicationApplicantInfo
    message: str | None
    status: ApplicationStatus
    created_at: datetime


class ApplicationListResponse(BaseModel):
    items: list[ApplicationListItem]
    total: int


# ─── 3.8 PATCH /matches/{match_id}/applications/{application_id} ─────────────


class ApplicationActionRequest(BaseModel):
    action: Literal["ACCEPT", "REJECT"]


class ApplicationActionResponse(BaseModel):
    application_id: int
    status: ApplicationStatus
    match_status: MatchStatus


# ─── 3.2 PATCH /matches/{match_id} ───────────────────────────────────────────


class MatchUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address: str | None = Field(default=None, max_length=255)
    desired_date: date | None = None
    pet_id: int | None = None

    @field_validator("latitude", "longitude")
    @classmethod
    def _finite(cls, v: float | None) -> float | None:
        return _validate_finite(v)

    @model_validator(mode="after")
    def check_lat_lng_pair(self) -> "MatchUpdateRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude와 longitude는 함께 보내야 합니다.")
        return self


# ─── 3.14 GET /users/me/volunteer-stats ──────────────────────────────────────


class VolunteerStatsResponse(BaseModel):
    total_count: int
    total_hours: float
    avg_rating: float | None
