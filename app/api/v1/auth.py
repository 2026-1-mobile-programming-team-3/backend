from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    SignupRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.signup(db, data)


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, data.email, data.password)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh(db, data)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await auth_service.logout(db, data)
    return MessageResponse(message="로그아웃되었습니다.")
