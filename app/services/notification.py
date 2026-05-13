from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import notification as notification_crud
from app.models.enums import NotificationCategory
from app.models.notification import Notification, NotificationSetting
from app.schemas.notification import (
    DeviceRegisteredResponse,
    DeviceRegisterRequest,
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)


async def _is_category_enabled(
    db: AsyncSession, *, user_id: int, category: NotificationCategory
) -> bool:
    """행이 없으면 ON(기본값)으로 간주."""
    stmt = select(NotificationSetting.push_enabled).where(
        NotificationSetting.user_id == user_id,
        NotificationSetting.category == category,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return True if row is None else bool(row)


async def enqueue(
    db: AsyncSession,
    *,
    user_id: int,
    category: NotificationCategory,
    title: str,
    body: str,
    link: str | None = None,
) -> Notification | None:
    """알림 1건을 DB에 적재. 호출자는 commit 책임을 가진다.

    사용자가 해당 카테고리를 OFF로 설정한 경우(`notification_settings.push_enabled=False`)
    적재 자체를 건너뛰고 `None`을 반환한다 — 인앱·푸시 모두 노출되지 않는다.
    행이 없으면 기본 ON.
    """
    if not await _is_category_enabled(db, user_id=user_id, category=category):
        return None
    notification = Notification(
        user_id=user_id,
        category=category,
        title=title,
        body=body,
        link=link,
    )
    db.add(notification)
    return notification


# ─── 마이페이지: 카테고리별 push 알림 설정 ────────────────────────────────────


async def get_notification_settings(
    db: AsyncSession, *, user_id: int
) -> dict[NotificationCategory, bool]:
    """모든 카테고리에 대한 push on/off — 행이 없는 카테고리는 True로 기본."""
    rows = await notification_crud.list_settings(db, user_id)
    saved = {row.category: row.push_enabled for row in rows}
    return {cat: saved.get(cat, True) for cat in NotificationCategory}


async def update_notification_settings(
    db: AsyncSession,
    *,
    user_id: int,
    updates: dict[NotificationCategory, bool],
) -> dict[NotificationCategory, bool]:
    await notification_crud.upsert_settings(
        db, user_id=user_id, updates=updates
    )
    return await get_notification_settings(db, user_id=user_id)


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
