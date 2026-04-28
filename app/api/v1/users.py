from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordChangeRequest,
    UserMeResponse,
    UserResponse,
    UserUpdateRequest,
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
