from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VolunteerRequestStatus
from app.models.user import User
from app.models.volunteer import VolunteerRequest


async def get_pending_by_user(db: AsyncSession, user_id: int) -> VolunteerRequest | None:
    result = await db.execute(
        select(VolunteerRequest).where(
            VolunteerRequest.user_id == user_id,
            VolunteerRequest.status == VolunteerRequestStatus.PENDING,
        )
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user_id: int, message: str) -> VolunteerRequest:
    req = VolunteerRequest(user_id=user_id, message=message)
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def get_by_id(db: AsyncSession, request_id: int) -> VolunteerRequest | None:
    result = await db.execute(
        select(VolunteerRequest).where(VolunteerRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def list_by_status(
    db: AsyncSession,
    status: VolunteerRequestStatus,
    page: int,
    size: int,
) -> tuple[list[tuple[VolunteerRequest, str]], int]:
    """페이지네이션된 ((request, nickname) 튜플 리스트, total) 반환."""
    count_result = await db.execute(
        select(func.count(VolunteerRequest.id)).where(VolunteerRequest.status == status)
    )
    total = int(count_result.scalar_one())

    offset = (page - 1) * size
    result = await db.execute(
        select(VolunteerRequest, User.nickname)
        .join(User, User.id == VolunteerRequest.user_id)
        .where(VolunteerRequest.status == status)
        .order_by(VolunteerRequest.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    rows = [(row[0], row[1]) for row in result.all()]
    return rows, total


async def update_status(
    db: AsyncSession,
    req: VolunteerRequest,
    new_status: VolunteerRequestStatus,
) -> VolunteerRequest:
    """status, processed_at 갱신. commit은 호출자 책임."""
    req.status = new_status
    req.processed_at = datetime.now(timezone.utc)
    return req
