from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.enums import StoreRequestStatus, VolunteerRequestStatus
from app.models.user import User
from app.schemas.admin import (
    VolunteerRequestActionRequest,
    VolunteerRequestListResponse,
    VolunteerRequestProcessedResponse,
)
from app.schemas.store_request import (
    StoreRequestActionRequest,
    StoreRequestAdminItem,
    StoreRequestAdminListResponse,
    StoreRequestProcessedResponse,
)
from app.services import store_request as store_request_service
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


# ─── 매장 추가/수정 요청 (Store Requests) ────────────────────────────────────

@router.get(
    "/store-requests", response_model=StoreRequestAdminListResponse
)
async def list_store_requests(
    status: StoreRequestStatus = Query(StoreRequestStatus.PENDING),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await store_request_service.list_admin_requests(
        db, status_filter=status, page=page, size=size
    )


@router.get(
    "/store-requests/{request_id}", response_model=StoreRequestAdminItem
)
async def get_store_request_detail(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await store_request_service.get_admin_request_detail(db, request_id)


@router.patch(
    "/store-requests/{request_id}",
    response_model=StoreRequestProcessedResponse,
)
async def process_store_request(
    request_id: int,
    body: StoreRequestActionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await store_request_service.process_admin_request(
        db,
        admin_user_id=admin.id,
        request_id=request_id,
        action=body.action,
        note=body.note,
    )
