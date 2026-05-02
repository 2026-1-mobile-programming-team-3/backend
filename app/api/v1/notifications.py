from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.enums import NotificationCategory
from app.models.user import User
from app.schemas.notification import (
    DeviceRegisteredResponse,
    DeviceRegisterRequest,
    MarkAllReadResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services import notification as notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.get_unread_count(
        db, user_id=current_user.id
    )


@router.patch("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.mark_all_read(
        db, user_id=current_user.id
    )


@router.post(
    "/devices",
    response_model=DeviceRegisteredResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    data: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.register_device(
        db, user_id=current_user.id, data=data
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    is_read: bool | None = Query(None),
    category: NotificationCategory | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.list_notifications(
        db,
        user_id=current_user.id,
        is_read=is_read,
        category=category,
        page=page,
        size=size,
    )
