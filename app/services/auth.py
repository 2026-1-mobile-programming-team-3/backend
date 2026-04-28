from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.crud import refresh_token as crud_rt
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.auth import (
    LoginResponse,
    LogoutRequest,
    SignupRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.schemas.user import AccountDeleteRequest, PasswordChangeRequest, UserUpdateRequest


async def signup(db: AsyncSession, data: SignupRequest) -> User:
    existing = await crud_user.get_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )
    return await crud_user.create(
        db,
        email=data.email,
        password_hash=hash_password(data.password),
        nickname=data.nickname,
        phone=data.phone,
    )


async def login(db: AsyncSession, email: str, password: str) -> LoginResponse:
    user = await crud_user.get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(user.id)
    raw_rt = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await crud_rt.create(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_rt),
        expires_at=expires_at,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_rt,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh(db: AsyncSession, data: TokenRefreshRequest) -> TokenRefreshResponse:
    token_record = await crud_rt.get_active_by_hash(db, hash_refresh_token(data.refresh_token))
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 refresh token입니다.",
        )

    access_token = create_access_token(token_record.user_id)
    return TokenRefreshResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def logout(db: AsyncSession, data: LogoutRequest) -> None:
    token_record = await crud_rt.get_active_by_hash(db, hash_refresh_token(data.refresh_token))
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 refresh token입니다.",
        )
    await crud_rt.revoke(db, token_record)


async def update_profile(db: AsyncSession, user: User, data: UserUpdateRequest) -> User:
    # exclude_unset: 클라이언트가 보내지 않은 필드는 제외
    # None 필터: null로 보낸 필드도 건너뜀 (nullable 컬럼 초기화는 별도 엔드포인트에서)
    fields = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not fields:
        return user
    return await crud_user.update(db, user, **fields)


async def change_password(db: AsyncSession, user: User, data: PasswordChangeRequest) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    await crud_user.update(db, user, password_hash=hash_password(data.new_password))


async def delete_account(db: AsyncSession, user: User, data: AccountDeleteRequest) -> None:
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
        )
    await crud_user.soft_delete(db, user)
