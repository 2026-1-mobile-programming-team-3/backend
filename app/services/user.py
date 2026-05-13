"""마이페이지 — 활동 통계 + 봉사 뱃지 어그리게이션."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.badge import compute_badge
from app.crud import favorite as favorite_crud
from app.crud import match as match_crud
from app.models.user import User
from app.schemas.user import ActivityStatsResponse, VolunteerBadgeInfo


async def get_activity_stats(
    db: AsyncSession, *, current_user: User
) -> ActivityStatsResponse:
    my_match_count = await match_crud.count_authored_matches(db, current_user.id)
    volunteer_completed = await match_crud.count_completed_volunteer_matches(
        db, current_user.id
    )
    favorite_count = await favorite_crud.count_active(db, current_user.id)

    badge = VolunteerBadgeInfo(**compute_badge(volunteer_completed))

    return ActivityStatsResponse(
        my_match_count=my_match_count,
        volunteer_completed_count=volunteer_completed,
        favorite_count=favorite_count,
        badge=badge,
    )
