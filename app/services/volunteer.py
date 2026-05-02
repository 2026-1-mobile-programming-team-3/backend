from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import user as crud_user
from app.crud import volunteer_request as crud_vr
from app.models.enums import UserRole, VolunteerRequestStatus
from app.models.volunteer import VolunteerRequest
from app.schemas.admin import (
    VolunteerRequestAdminItem,
    VolunteerRequestListResponse,
)


async def list_admin_requests(
    db: AsyncSession,
    status_filter: VolunteerRequestStatus,
    page: int,
    size: int,
) -> VolunteerRequestListResponse:
    rows, total = await crud_vr.list_by_status(db, status_filter, page, size)
    items = [
        VolunteerRequestAdminItem(
            id=req.id,
            user_id=req.user_id,
            nickname=nickname,
            message=req.message,
            status=req.status,
            created_at=req.created_at,
            processed_at=req.processed_at,
        )
        for req, nickname in rows
    ]
    return VolunteerRequestListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )


async def process_admin_request(
    db: AsyncSession,
    request_id: int,
    action: Literal["APPROVE", "REJECT"],
) -> VolunteerRequest:
    req = await crud_vr.get_by_id(db, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="봉사자 요청을 찾을 수 없습니다.",
        )
    if req.status != VolunteerRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리된 요청입니다.",
        )

    if action == "APPROVE":
        await crud_vr.update_status(db, req, VolunteerRequestStatus.APPROVED)
        user = await crud_user.get_by_id(db, req.user_id)
        if user is not None and user.role == UserRole.USER:
            user.role = UserRole.VOLUNTEER
    else:
        await crud_vr.update_status(db, req, VolunteerRequestStatus.REJECTED)

    await db.commit()
    await db.refresh(req)
    return req
