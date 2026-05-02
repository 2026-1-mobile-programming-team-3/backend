from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VolunteerRequestStatus


class VolunteerRequestAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    request_id: int = Field(alias="id")
    user_id: int
    nickname: str
    message: str
    status: VolunteerRequestStatus
    submitted_at: datetime = Field(alias="created_at")
    processed_at: datetime | None = None


class VolunteerRequestListResponse(BaseModel):
    items: list[VolunteerRequestAdminItem]
    total: int
    page: int
    size: int


class VolunteerRequestActionRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    admin_comment: str | None = None


class VolunteerRequestProcessedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    request_id: int = Field(alias="id")
    user_id: int
    status: VolunteerRequestStatus
    processed_at: datetime
