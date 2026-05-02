from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import UserBlock
from app.models.user import User


async def create(
    db: AsyncSession,
    *,
    blocker_id: int,
    blocked_id: int,
) -> UserBlock:
    """unique(blocker_id, blocked_id) 위반 시 IntegrityError — 호출자가 잡아 409 변환."""
    block = UserBlock(blocker_id=blocker_id, blocked_id=blocked_id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def list_by_user(
    db: AsyncSession,
    user_id: int,
) -> list[tuple[UserBlock, str | None]]:
    """(block, blocked_user_nickname) created_at DESC."""
    stmt = (
        select(UserBlock, User.nickname)
        .outerjoin(
            User,
            (User.id == UserBlock.blocked_id) & (User.deleted_at.is_(None)),
        )
        .where(UserBlock.blocker_id == user_id)
        .order_by(UserBlock.created_at.desc())
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_by_id(db: AsyncSession, block_id: int) -> UserBlock | None:
    stmt = select(UserBlock).where(UserBlock.id == block_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, block: UserBlock) -> None:
    """commit은 호출자 책임."""
    await db.delete(block)
