from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationCategory
from app.models.notification import Notification
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
