from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.block import (
    BlockCreatedResponse,
    BlockCreateRequest,
    BlockListResponse,
)
from app.services import block as block_service

router = APIRouter(prefix="/users/me/blocks", tags=["blocks"])


@router.post(
    "",
    response_model=BlockCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/hour")
async def create_block(
    request: Request,
    data: BlockCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await block_service.create_block(
        db, current_user=current_user, data=data
    )


@router.get("", response_model=BlockListResponse)
async def list_blocks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await block_service.list_blocks(db, user_id=current_user.id)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await block_service.delete_block(
        db, user_id=current_user.id, block_id=block_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
