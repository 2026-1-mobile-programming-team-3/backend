"""홈 대시보드 어그리게이션. 외부 API(날씨/산책지수)는 stub. 일부 캐시는 Redis."""
from __future__ import annotations

from datetime import datetime, timezone
from math import sin

import redis.asyncio as aioredis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_or_set_json
from app.crud import match as match_crud
from app.crud import notification as notification_crud
from app.models.enums import UserRole
from app.models.store import Store
from app.models.user import User
from app.schemas.home import (
    HomeDashboardResponse,
    HomeMatchAsApplicant,
    HomeMatchAsAuthor,
    HomeMatchSummary,
    HomeUserContext,
    HomeVolunteerStats,
    HomeWeather,
)


_WALK_SCORE_TTL = 60 * 10  # 10분 (이전 30분 → 단축)
_WEATHER_TTL = 60 * 10  # 10분 (이전 30분 → 단축)
_NEARBY_STORE_TTL = 60 * 3  # 3분 (이전 5분 → 단축)


async def _walk_score_stub(user_id: int) -> int:
    """외부 API 미연동. 사용자 id를 시드로 0~100 사이 안정적 값을 생성."""
    raw = abs(sin(float(user_id) + 1.0))
    return int(60 + raw * 40)


async def _weather_stub(region_dong: str | None) -> dict:
    """외부 API 미연동. 단순 stub. source='stub' 으로 명시."""
    return {
        "condition": "CLEAR",
        "temp_c": 20.0,
        "dust_grade": "GOOD",
        "source": "stub",
    }


async def _nearby_store_count(db: AsyncSession, region_dong: str | None) -> int:
    if not region_dong:
        # 전체 매장 수로 fallback.
        stmt = select(func.count()).select_from(Store)
    else:
        stmt = (
            select(func.count())
            .select_from(Store)
            .where(Store.address.ilike(f"%{region_dong}%"))
        )
    return int((await db.execute(stmt)).scalar_one())


async def get_dashboard(
    db: AsyncSession,
    *,
    current_user: User,
    redis: aioredis.Redis,
) -> HomeDashboardResponse:
    user_ctx = HomeUserContext(
        nickname=current_user.nickname,
        role=current_user.role,
        region_si=current_user.region_si,
        region_dong=current_user.region_dong,
    )

    walk_key = f"walk_score:{current_user.id}"
    walk_score = (
        None
        if not current_user.region_dong
        else await get_or_set_json(
            redis,
            key=walk_key,
            ttl_seconds=_WALK_SCORE_TTL,
            factory=lambda: _walk_score_stub(current_user.id),
        )
    )

    weather_key = (
        f"weather:{current_user.region_dong}"
        if current_user.region_dong
        else None
    )
    weather: HomeWeather | None = None
    if weather_key is not None:
        weather_dict = await get_or_set_json(
            redis,
            key=weather_key,
            ttl_seconds=_WEATHER_TTL,
            factory=lambda: _weather_stub(current_user.region_dong),
        )
        weather = HomeWeather(**weather_dict)

    store_key = f"stores:nearby:{current_user.region_dong or 'all'}"
    nearby_store_count = await get_or_set_json(
        redis,
        key=store_key,
        ttl_seconds=_NEARBY_STORE_TTL,
        factory=lambda: _nearby_store_count(db, current_user.region_dong),
    )

    # 내 매칭 요약
    as_author_row = await match_crud.latest_active_match_as_author(db, current_user.id)
    as_applicant_row = await match_crud.latest_active_match_as_applicant(db, current_user.id)
    summary = HomeMatchSummary(
        as_author=(
            HomeMatchAsAuthor(
                match_id=as_author_row[0].id,
                title=as_author_row[0].title,
                desired_date=as_author_row[0].desired_date,
                status=as_author_row[0].status,
                applications_count=as_author_row[1],
            )
            if as_author_row is not None
            else None
        ),
        as_applicant=(
            HomeMatchAsApplicant(
                match_id=as_applicant_row[0].id,
                title=as_applicant_row[0].title,
                desired_date=as_applicant_row[0].desired_date,
                status=as_applicant_row[0].status,
                my_application_status=as_applicant_row[1],
            )
            if as_applicant_row is not None
            else None
        ),
    )

    volunteer_stats = None
    if current_user.role in (UserRole.VOLUNTEER, UserRole.ADMIN):
        total = await match_crud.count_completed_volunteer_matches(db, current_user.id)
        avg = await match_crud.avg_review_rating_for(db, current_user.id)
        volunteer_stats = HomeVolunteerStats(total_count=total, avg_rating=avg)

    unread = await notification_crud.count_unread(db, current_user.id)

    return HomeDashboardResponse(
        user=user_ctx,
        walk_score=walk_score,
        weather=weather,
        nearby_store_count=int(nearby_store_count),
        my_match_summary=summary,
        volunteer_stats=volunteer_stats,
        unread_notification_count=unread,
        generated_at=datetime.now(timezone.utc),
    )
