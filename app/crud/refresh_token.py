from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_active_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def revoke(db: AsyncSession, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(timezone.utc)
    await db.commit()


async def rotate(
    db: AsyncSession,
    *,
    old: RefreshToken,
    new_token_hash: str,
    new_expires_at: datetime,
) -> RefreshToken:
    """기존 토큰을 폐기하고 신규 토큰을 동일 트랜잭션에서 발급."""
    old.revoked_at = datetime.now(timezone.utc)
    new_token = RefreshToken(
        user_id=old.user_id,
        token_hash=new_token_hash,
        expires_at=new_expires_at,
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    return new_token


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> int:
    """비밀번호 변경/탈퇴 시 해당 사용자의 모든 활성 refresh를 일괄 폐기."""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    await db.commit()
    return int(result.rowcount or 0)
