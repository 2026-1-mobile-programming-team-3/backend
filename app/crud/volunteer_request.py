from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VolunteerRequestStatus
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
