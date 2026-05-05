from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.enums import MatchStatus
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.match import (
    ApplicationActionRequest,
    ApplicationActionResponse,
    ApplicationCreatedResponse,
    ApplicationCreateRequest,
    ApplicationListResponse,
    MatchCreatedResponse,
    MatchCreateRequest,
    MatchDetail,
    MatchListResponse,
    MatchUpdateRequest,
)
from app.services import match as match_service

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post(
    "",
    response_model=MatchCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_match(
    data: MatchCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.create_match(
        db, current_user_id=current_user.id, data=data
    )


@router.get("", response_model=MatchListResponse)
async def list_matches(
    status_filter: MatchStatus | None = Query(None, alias="status"),
    region: str | None = Query(None, max_length=50),
    from_date: date_type | None = Query(None),
    to_date: date_type | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.list_matches(
        db,
        current_user=current_user,
        status_filter=status_filter,
        region=region,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await match_service.get_match_detail(db, match_id)


@router.patch("/{match_id}", response_model=MessageResponse)
async def update_match(
    match_id: int,
    data: MatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.update_match(
        db, current_user=current_user, match_id=match_id, data=data
    )


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await match_service.delete_match(
        db, current_user=current_user, match_id=match_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{match_id}/applications",
    response_model=ApplicationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_application(
    match_id: int,
    data: ApplicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.create_application(
        db, current_user_id=current_user.id, match_id=match_id, data=data
    )


@router.get(
    "/{match_id}/applications", response_model=ApplicationListResponse
)
async def list_applications(
    match_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.list_applications(
        db, current_user=current_user, match_id=match_id, page=page, size=size
    )


@router.patch(
    "/{match_id}/applications/{application_id}",
    response_model=ApplicationActionResponse,
)
async def respond_application(
    match_id: int,
    application_id: int,
    data: ApplicationActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await match_service.respond_application(
        db,
        current_user=current_user,
        match_id=match_id,
        application_id=application_id,
        data=data,
    )
