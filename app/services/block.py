from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import block as block_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.block import (
    BlockCreatedResponse,
    BlockCreateRequest,
    BlockListItem,
    BlockListResponse,
)


async def create_block(
    db: AsyncSession,
    *,
    current_user: User,
    data: BlockCreateRequest,
) -> BlockCreatedResponse:
    if data.target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인을 차단할 수 없습니다.",
        )
    target = await user_crud.get_by_id(db, data.target_user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 사용자를 찾을 수 없습니다.",
        )
    try:
        block = await block_crud.create(
            db,
            blocker_id=current_user.id,
            blocked_id=data.target_user_id,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 차단한 사용자입니다.",
        )
    return BlockCreatedResponse(
        block_id=block.id,
        target_user_id=block.blocked_id,
        created_at=block.created_at,
    )


async def list_blocks(
    db: AsyncSession,
    *,
    user_id: int,
    page: int,
    size: int,
) -> BlockListResponse:
    rows, total = await block_crud.list_by_user(db, user_id, page=page, size=size)
    items = [
        BlockListItem(
            block_id=block.id,
            target_user_id=block.blocked_id,
            target_nickname=nickname,
            created_at=block.created_at,
        )
        for block, nickname in rows
    ]
    return BlockListResponse(items=items, total=total, page=page, size=size)


async def delete_block(
    db: AsyncSession,
    *,
    user_id: int,
    block_id: int,
) -> None:
    block = await block_crud.get_by_id(db, block_id)
    if block is None or block.blocker_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="차단 정보를 찾을 수 없습니다.",
        )
    await block_crud.delete(db, block)
    await db.commit()
