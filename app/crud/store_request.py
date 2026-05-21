from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StoreRequestStatus, StoreRequestType
from app.models.store_request import StoreRequest
from app.models.user import User


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    type_: StoreRequestType,
    target_store_id: int | None,
    payload: dict[str, Any],
    proof_urls: list[str],
    message: str | None,
) -> StoreRequest:
    """status=PENDING 으로 INSERT. PENDING 중복 unique 위반 시 IntegrityError 발생."""
    req = StoreRequest(
        user_id=user_id,
        type=type_,
        target_store_id=target_store_id,
        payload=payload,
        proof_urls=proof_urls,
        message=message,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def get_by_id(db: AsyncSession, request_id: int) -> StoreRequest | None:
    result = await db.execute(
        select(StoreRequest).where(StoreRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def list_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    status_filter: StoreRequestStatus | None,
    page: int,
    size: int,
) -> tuple[list[StoreRequest], int]:
    base = select(StoreRequest).where(StoreRequest.user_id == user_id)
    count_q = select(func.count(StoreRequest.id)).where(StoreRequest.user_id == user_id)
    if status_filter is not None:
        base = base.where(StoreRequest.status == status_filter)
        count_q = count_q.where(StoreRequest.status == status_filter)
    total = int((await db.execute(count_q)).scalar_one())
    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(StoreRequest.created_at.desc()).offset(offset).limit(size)
    )
    return list(result.scalars().all()), total


async def list_for_admin(
    db: AsyncSession,
    *,
    status_filter: StoreRequestStatus,
    page: int,
    size: int,
) -> tuple[list[tuple[StoreRequest, str | None]], int]:
    """(request, nickname) 페이지네이션. 탈퇴 사용자 nickname=None."""
    count_q = select(func.count(StoreRequest.id)).where(
        StoreRequest.status == status_filter
    )
    total = int((await db.execute(count_q)).scalar_one())
    offset = (page - 1) * size
    result = await db.execute(
        select(StoreRequest, User.nickname)
        .outerjoin(
            User,
            (User.id == StoreRequest.user_id) & (User.deleted_at.is_(None)),
        )
        .where(StoreRequest.status == status_filter)
        .order_by(StoreRequest.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    rows = [(row[0], row[1]) for row in result.all()]
    return rows, total


async def update_status(
    db: AsyncSession,
    req: StoreRequest,
    *,
    new_status: StoreRequestStatus,
    reviewer_id: int,
    note: str | None,
) -> StoreRequest:
    """status, processed_at, reviewer_id, review_note 갱신. commit은 호출자."""
    req.status = new_status
    req.processed_at = datetime.now(timezone.utc)
    req.reviewer_id = reviewer_id
    if note is not None:
        req.review_note = note
    return req


async def delete(db: AsyncSession, req: StoreRequest) -> None:
    """본인 PENDING 요청 취소. commit은 호출자."""
    await db.delete(req)
