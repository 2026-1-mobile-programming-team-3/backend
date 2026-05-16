import asyncio
import logging

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import firebase as fcm
from app.crud import notification as notification_crud
from app.models.enums import NotificationCategory
from app.models.notification import Notification, NotificationSetting
from app.models.user import Device
from app.schemas.notification import (
    DeviceRegisteredResponse,
    DeviceRegisterRequest,
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


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
    data: dict[str, str] | None = None,
    push: bool = True,
) -> Notification | None:
    """알림 1건을 DB에 적재하고 (선택) FCM 푸시를 commit 후로 스케줄.

    사용자가 해당 카테고리를 OFF로 설정한 경우(`notification_settings.push_enabled=False`)
    적재 자체를 건너뛰고 `None`을 반환한다 — 인앱·푸시 모두 노출되지 않는다.
    행이 없으면 기본 ON.

    푸시 발송은 `push=True` 이고 Firebase 가 ready 일 때만 등록되며,
    `db.commit()` 성공 직후 db/session.py 의 after_commit 훅이 fire-and-forget 실행한다.
    rollback 시에는 자동으로 폐기.
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

    if push and fcm.is_ready():
        payload = {
            "category": category.value if hasattr(category, "value") else str(category),
            "link": link or "",
        }
        if data:
            for k, v in data.items():
                payload.setdefault(k, "" if v is None else str(v))
        pending = db.sync_session.info.setdefault("pending_pushes", [])
        pending.append(_make_push_closure(user_id, title, body, payload))

    return notification


def _make_push_closure(user_id: int, title: str, body: str, data: dict[str, str]):
    """after_commit 시점에 호출될 비동기 함수 팩토리."""

    async def _push() -> None:
        try:
            await _dispatch_push_to_user(
                user_id=user_id, title=title, body=body, data=data
            )
        except Exception:
            logger.exception("FCM dispatch 실패 (user_id=%s)", user_id)

    return _push


async def _dispatch_push_to_user(
    *, user_id: int, title: str, body: str, data: dict[str, str]
) -> None:
    """별도 세션을 열어 사용자의 device 토큰을 가져와 FCM 발송. 무효 토큰은 삭제."""
    if not fcm.is_ready():
        return
    # 요청 세션은 이미 닫혔을 가능성이 높아 새 세션을 연다.
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Device.fcm_token).where(Device.user_id == user_id)
        )
        tokens = [t for t in rows.scalars().all() if t]
        if not tokens:
            return
        # firebase-admin 은 blocking 이므로 worker thread 로 위임.
        invalid = await asyncio.to_thread(
            fcm.send_to_tokens, tokens, title=title, body=body, data=data
        )
        if invalid:
            await db.execute(delete(Device).where(Device.fcm_token.in_(invalid)))
            await db.commit()


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


async def mark_one_read(
    db: AsyncSession, *, user_id: int, notification_id: int
) -> dict:
    """단건 읽음 처리. 본인 소유 아니면 404. 이미 읽은 알림은 멱등 처리."""
    found, was_unread = await notification_crud.mark_one_read(
        db, user_id=user_id, notification_id=notification_id
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 알림을 찾을 수 없습니다.",
        )
    return {
        "id": notification_id,
        "is_read": True,
        "updated": was_unread,
    }
