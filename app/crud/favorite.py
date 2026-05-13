from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StoreStatus
from app.models.favorite import StoreFavorite
from app.models.store import Store


async def create(
    db: AsyncSession, *, user_id: int, store_id: int
) -> StoreFavorite:
    """unique(user_id, store_id) 위반 시 IntegrityError — 호출자가 잡아 409 변환."""
    fav = StoreFavorite(user_id=user_id, store_id=store_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


async def get_by_user_store(
    db: AsyncSession, *, user_id: int, store_id: int
) -> StoreFavorite | None:
    stmt = select(StoreFavorite).where(
        StoreFavorite.user_id == user_id,
        StoreFavorite.store_id == store_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def delete(db: AsyncSession, fav: StoreFavorite) -> None:
    await db.delete(fav)
    await db.commit()


async def count_active(db: AsyncSession, user_id: int) -> int:
    """본인 즐겨찾기 중 매장이 살아있고 승인된 것의 수."""
    stmt = (
        select(func.count())
        .select_from(StoreFavorite)
        .join(Store, Store.id == StoreFavorite.store_id)
        .where(
            StoreFavorite.user_id == user_id,
            Store.deleted_at.is_(None),
            Store.status == StoreStatus.APPROVED,
        )
    )
    return int((await db.execute(stmt)).scalar_one())


async def list_active(
    db: AsyncSession,
    *,
    user_id: int,
    page: int,
    size: int,
) -> tuple[list[tuple[StoreFavorite, Store]], int]:
    """매장이 살아있고 승인된 즐겨찾기만 반환. created_at DESC + 총 개수."""
    base_filters = [
        StoreFavorite.user_id == user_id,
        Store.deleted_at.is_(None),
        Store.status == StoreStatus.APPROVED,
    ]

    count_stmt = (
        select(func.count())
        .select_from(StoreFavorite)
        .join(Store, Store.id == StoreFavorite.store_id)
        .where(*base_filters)
    )
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(StoreFavorite, Store)
        .join(Store, Store.id == StoreFavorite.store_id)
        .where(*base_filters)
        .order_by(StoreFavorite.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    rows = [(row[0], row[1]) for row in result.all()]
    return rows, total
