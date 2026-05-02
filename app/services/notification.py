from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import notification as notification_crud
from app.models.enums import NotificationCategory
from app.schemas.notification import (
    DeviceRegisteredResponse,
    DeviceRegisterRequest,
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)


async def list_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    is_read: bool | None,
    category: NotificationCategory | None,
    page: int,
    size: int,
) -> NotificationListResponse:
    notifications, total = await notification_crud.list_notifications(
        db,
        user_id=user_id,
        is_read=is_read,
        category=category,
        page=page,
        size=size,
    )
    unread_count = await notification_crud.count_unread(db, user_id)
    items = [
        NotificationItem(
            id=n.id,
            category=n.category,
            title=n.title,
            body=n.body,
            is_read=n.read_at is not None,
            link=n.link,
            created_at=n.created_at,
        )
        for n in notifications
    ]
    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        size=size,
    )


async def get_unread_count(
    db: AsyncSession, *, user_id: int
) -> UnreadCountResponse:
    count = await notification_crud.count_unread(db, user_id)
    return UnreadCountResponse(unread_count=count)


async def register_device(
    db: AsyncSession,
    *,
    user_id: int,
    data: DeviceRegisterRequest,
) -> DeviceRegisteredResponse:
    existing = await notification_crud.get_device_by_token(db, data.fcm_token)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 토큰입니다.",
        )
    try:
        device = await notification_crud.create_device(
            db,
            user_id=user_id,
            fcm_token=data.fcm_token,
            device_name=data.device_name,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 토큰입니다.",
        )
    return DeviceRegisteredResponse(id=device.id, registered_at=device.created_at)


async def mark_all_read(
    db: AsyncSession, *, user_id: int
) -> MarkAllReadResponse:
    count = await notification_crud.mark_all_read(db, user_id)
    return MarkAllReadResponse(
        updated_count=count,
        message=f"{count}건의 알림을 읽음 처리했습니다.",
    )
