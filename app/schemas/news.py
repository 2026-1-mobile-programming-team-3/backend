from pydantic import BaseModel, ConfigDict


class NewsItem(BaseModel):
    news_id: str        # sha256(link)[:12]
    title: str
    summary: str
    published_date: str  # "YYYY-MM-DD"
    link: str


class NewsListResponse(BaseModel):
    news: list[NewsItem]


class NewsDetail(BaseModel):
    news_id: str
    title: str
    content: str
    official_link: str
    published_date: str


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    title: str
    start_date: str
    end_date: str


class CalendarMonthResponse(BaseModel):
    events: list[CalendarEventOut]


class DailyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    title: str
    description: str | None
    time: str | None  # "HH:MM"


class DailyEventsResponse(BaseModel):
    daily_events: list[DailyEventOut]
