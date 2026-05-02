from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.enums import VolunteerRequestStatus
from app.models.user import User
from app.schemas.admin import (
    VolunteerRequestActionRequest,
    VolunteerRequestListResponse,
    VolunteerRequestProcessedResponse,
)
from app.services import volunteer as volunteer_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/volunteer-requests", response_model=VolunteerRequestListResponse)
async def list_volunteer_requests(
    status: VolunteerRequestStatus = Query(VolunteerRequestStatus.PENDING),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await volunteer_service.list_admin_requests(db, status, page, size)


@router.patch(
    "/volunteer-requests/{request_id}",
    response_model=VolunteerRequestProcessedResponse,
)
async def process_volunteer_request(
    request_id: int,
    body: VolunteerRequestActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await volunteer_service.process_admin_request(db, request_id, body.action)
