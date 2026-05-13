from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.favorite import (
    FavoriteCreatedResponse,
    FavoriteCreateRequest,
    FavoriteListResponse,
)
from app.services import favorite as favorite_service

router = APIRouter(prefix="/users/me/favorites", tags=["favorites"])


@router.post(
    "/stores",
    response_model=FavoriteCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_store_favorite(
    data: FavoriteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await favorite_service.create_favorite(
        db, user_id=current_user.id, data=data
    )


@router.delete("/stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store_favorite(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await favorite_service.delete_favorite(
        db, user_id=current_user.id, store_id=store_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/stores", response_model=FavoriteListResponse)
async def list_store_favorites(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await favorite_service.list_favorites(
        db, user_id=current_user.id, page=page, size=size
    )
