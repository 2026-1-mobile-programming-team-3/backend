from datetime import date as date_type
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ApplicationStatus, MatchStatus, UserRole


WeatherCondition = Literal["CLEAR", "CLOUDY", "RAIN", "SNOW"]
DustGrade = Literal["GOOD", "NORMAL", "BAD", "VERY_BAD"]


class HomeUserContext(BaseModel):
    nickname: str | None
    role: UserRole
    region_si: str | None
    region_dong: str | None


class HomeWeather(BaseModel):
    condition: WeatherCondition
    temp_c: float
    dust_grade: DustGrade
    source: Literal["stub", "live"] = "stub"


class HomeMatchAsAuthor(BaseModel):
    match_id: int
    title: str
    desired_date: date_type | None
    status: MatchStatus
    applications_count: int


class HomeMatchAsApplicant(BaseModel):
    match_id: int
    title: str
    desired_date: date_type | None
    status: MatchStatus
    my_application_status: ApplicationStatus


class HomeMatchSummary(BaseModel):
    as_author: HomeMatchAsAuthor | None
    as_applicant: HomeMatchAsApplicant | None


class HomeVolunteerStats(BaseModel):
    total_count: int
    avg_rating: float | None


class HomeDashboardResponse(BaseModel):
    user: HomeUserContext
    walk_score: int | None
    weather: HomeWeather | None
    nearby_store_count: int
    my_match_summary: HomeMatchSummary
    volunteer_stats: HomeVolunteerStats | None
    unread_notification_count: int
    generated_at: datetime
