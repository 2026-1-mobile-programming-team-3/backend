from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.crud import volunteer_request as crud_vr
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordChangeRequest,
    UserMeResponse,
    UserResponse,
    UserUpdateRequest,
    VolunteerRequestCreate,
    VolunteerRequestResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User).options(selectinload(User.pets)).where(User.id == current_user.id)
    )
    return result.scalar_one()


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await auth_service.update_profile(db, current_user, data)


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_service.change_password(db, current_user, data)
    return MessageResponse(message="비밀번호가 변경되었습니다.")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    data: AccountDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_service.delete_account(db, current_user, data)
    return MessageResponse(message="계정이 비활성화되었습니다. 30일 후 영구 삭제됩니다.")


@router.post("/me/volunteer-request", response_model=VolunteerRequestResponse, status_code=201)
async def request_volunteer_role(
    data: VolunteerRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in (UserRole.VOLUNTEER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 봉사자 또는 관리자 권한을 보유하고 있습니다.",
        )
    existing = await crud_vr.get_pending_by_user(db, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리 대기 중인 봉사자 전환 요청이 있습니다.",
        )
    return await crud_vr.create(db, user_id=current_user.id, message=data.message)
