from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationCategory
from app.models.notification import Notification, NotificationSetting
from app.models.user import Device


async def list_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    is_read: bool | None,
    category: NotificationCategory | None,
    page: int,
    size: int,
) -> tuple[list[Notification], int]:
    """필터 적용한 알림 페이지 + 총 개수. created_at DESC."""
    filters = [Notification.user_id == user_id]
    if is_read is True:
        filters.append(Notification.read_at.is_not(None))
    elif is_read is False:
        filters.append(Notification.read_at.is_(None))
    if category is not None:
        filters.append(Notification.category == category)

    count_stmt = select(func.count()).select_from(Notification).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), int(total)


async def count_unread(db: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return int((await db.execute(stmt)).scalar_one())


async def get_device_by_token(
    db: AsyncSession, fcm_token: str
) -> Device | None:
    stmt = select(Device).where(Device.fcm_token == fcm_token)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_device(
    db: AsyncSession,
    *,
    user_id: int,
    fcm_token: str,
    device_name: str | None,
) -> Device:
    device = Device(
        user_id=user_id,
        fcm_token=fcm_token,
        device_name=device_name,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    """안 읽은 알림을 모두 읽음 처리하고 변경된 행 수 반환."""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    await db.commit()
    return int(result.rowcount or 0)


async def mark_one_read(
    db: AsyncSession, *, user_id: int, notification_id: int
) -> tuple[bool, bool]:
    """단건 알림을 읽음 처리. 반환: (found, was_unread).

    - found=False: 본인 소유의 해당 알림 없음 (404)
    - found=True, was_unread=True: 이번 호출로 read_at 갱신됨
    - found=True, was_unread=False: 이미 읽은 상태였음 (멱등)
    """
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if notif is None:
        return (False, False)
    if notif.read_at is not None:
        return (True, False)
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    return (True, True)


# ─── NotificationSetting CRUD ────────────────────────────────────────────────


async def list_settings(
    db: AsyncSession, user_id: int
) -> list[NotificationSetting]:
    stmt = select(NotificationSetting).where(NotificationSetting.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


async def upsert_settings(
    db: AsyncSession,
    *,
    user_id: int,
    updates: dict[NotificationCategory, bool],
) -> list[NotificationSetting]:
    """upsert: 기존 행이 있으면 갱신, 없으면 신규. 누락된 카테고리는 변경 없음."""
    if not updates:
        return await list_settings(db, user_id)

    now = datetime.now(timezone.utc)
    existing = {
        s.category: s for s in await list_settings(db, user_id)
    }
    for category, enabled in updates.items():
        row = existing.get(category)
        if row is None:
            row = NotificationSetting(
                user_id=user_id,
                category=category,
                push_enabled=enabled,
            )
            db.add(row)
            existing[category] = row
        else:
            row.push_enabled = enabled
            row.updated_at = now
    await db.commit()
    return list(existing.values())
