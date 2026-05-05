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


async def list_blocked_ids(db: AsyncSession, user_id: int) -> list[int]:
    """user_id가 차단한 사용자 id 목록. 가시성 쿼리에서 NOT IN 필터로 사용."""
    stmt = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user_id)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def list_blocker_ids(db: AsyncSession, user_id: int) -> list[int]:
    """user_id를 차단한 사용자 id 목록. 양방향 가시성 차단 시 사용."""
    stmt = select(UserBlock.blocker_id).where(UserBlock.blocked_id == user_id)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def list_two_way_excluded_ids(db: AsyncSession, user_id: int) -> list[int]:
    """user_id 기준 양방향(차단함 ∪ 차단당함) 가시성 제외 id 합집합."""
    blocked = await list_blocked_ids(db, user_id)
    blockers = await list_blocker_ids(db, user_id)
    return list({*blocked, *blockers})


async def delete(db: AsyncSession, block: UserBlock) -> None:
    """commit은 호출자 책임."""
    await db.delete(block)
