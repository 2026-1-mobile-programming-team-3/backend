from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.deps import get_db, get_redis
from app.schemas.news import (
    CalendarMonthResponse,
    DailyEventsResponse,
    NewsDetail,
    NewsListResponse,
)
from app.services import news as news_service

router = APIRouter(prefix="/news", tags=["News"])


# /news/calendar 와 /news/calendar/daily 를 /{news_id} 보다 먼저 등록해야
# FastAPI가 경로 문자열을 path parameter로 오해하지 않는다.
@router.get("/calendar", response_model=CalendarMonthResponse)
async def get_calendar_month(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await news_service.get_calendar_events_by_month(db, year, month)


@router.get("/calendar/daily", response_model=DailyEventsResponse)
async def get_calendar_daily(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    return await news_service.get_daily_events(db, date)


@router.get("", response_model=NewsListResponse)
async def get_news_list(redis: aioredis.Redis = Depends(get_redis)):
    return await news_service.get_news_list(redis)


@router.get("/{news_id}", response_model=NewsDetail)
async def get_news_detail(
    news_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    return await news_service.get_news_detail(redis, news_id)
