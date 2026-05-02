from pydantic import BaseModel

from app.models.enums import MatchStatus


class VolunteerLocationItem(BaseModel):
    request_id: int
    title: str
    latitude: float
    longitude: float
    status: MatchStatus


class VolunteerLocationListResponse(BaseModel):
    volunteer_requests: list[VolunteerLocationItem]
