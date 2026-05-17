from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_by_nickname(db: AsyncSession, nickname: str) -> User | None:
    result = await db.execute(
        select(User).where(User.nickname == nickname, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str,
    nickname: str,
    phone: str | None,
    region_si: str | None = None,
    region_dong: str | None = None,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        nickname=nickname,
        phone=phone,
        region_si=region_si,
        region_dong=region_dong,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update(db: AsyncSession, user: User, **fields) -> User:
    for key, value in fields.items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def soft_delete(db: AsyncSession, user: User) -> None:
    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
