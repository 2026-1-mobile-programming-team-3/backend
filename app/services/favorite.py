from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import favorite as favorite_crud
from app.models.enums import StoreStatus
from app.models.store import Store
from app.schemas.favorite import (
    FavoriteCreatedResponse,
    FavoriteCreateRequest,
    FavoriteListItem,
    FavoriteListResponse,
)


async def create_favorite(
    db: AsyncSession,
    *,
    user_id: int,
    data: FavoriteCreateRequest,
) -> FavoriteCreatedResponse:
    stmt = select(Store).where(Store.id == data.store_id, Store.deleted_at.is_(None))
    store = (await db.execute(stmt)).scalar_one_or_none()
    if store is None or store.status != StoreStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매장을 찾을 수 없습니다.",
        )
    try:
        fav = await favorite_crud.create(db, user_id=user_id, store_id=data.store_id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 즐겨찾기에 등록된 매장입니다.",
        )
    return FavoriteCreatedResponse(
        favorite_id=fav.id, store_id=fav.store_id, created_at=fav.created_at
    )


async def delete_favorite(
    db: AsyncSession,
    *,
    user_id: int,
    store_id: int,
) -> None:
    fav = await favorite_crud.get_by_user_store(
        db, user_id=user_id, store_id=store_id
    )
    if fav is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="본인 즐겨찾기에 해당 매장이 없습니다.",
        )
    await favorite_crud.delete(db, fav)


async def list_favorites(
    db: AsyncSession,
    *,
    user_id: int,
    page: int,
    size: int,
) -> FavoriteListResponse:
    rows, total = await favorite_crud.list_active(
        db, user_id=user_id, page=page, size=size
    )
    items = [
        FavoriteListItem(
            favorite_id=fav.id,
            store_id=store.id,
            name=store.name,
            category=store.category,
            thumbnail_url=(store.photo_urls[0] if store.photo_urls else None),
            rating_avg=store.rating_avg,
            created_at=fav.created_at,
        )
        for fav, store in rows
    ]
    return FavoriteListResponse(items=items, total=total, page=page, size=size)
