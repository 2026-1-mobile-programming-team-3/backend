from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.enums import StoreRequestStatus
from app.models.user import User
from app.schemas.store_request import (
    StoreRequestCreate,
    StoreRequestCreatedResponse,
    StoreRequestItem,
    StoreRequestListResponse,
)
from app.services import store_request as store_request_service

router = APIRouter(prefix="/maps/store-requests", tags=["StoreRequests"])


@router.post(
    "",
    response_model=StoreRequestCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def create_store_request(
    request: Request,
    data: StoreRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_request_service.create_request(
        db, current_user_id=current_user.id, data=data
    )


@router.get("", response_model=StoreRequestListResponse)
async def list_my_store_requests(
    status_filter: StoreRequestStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_request_service.list_my_requests(
        db,
        current_user_id=current_user.id,
        status_filter=status_filter,
        page=page,
        size=size,
    )


@router.get("/{request_id}", response_model=StoreRequestItem)
async def get_my_store_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await store_request_service.get_my_request(
        db, current_user_id=current_user.id, request_id=request_id
    )


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_my_store_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await store_request_service.cancel_my_request(
        db, current_user_id=current_user.id, request_id=request_id
    )
