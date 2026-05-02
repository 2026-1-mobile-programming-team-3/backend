from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    target_user_id: int
    reason: str = Field(min_length=1, max_length=2000)


class ReportCreatedResponse(BaseModel):
    id: int
    target_user_id: int
    reason: str
    created_at: datetime
