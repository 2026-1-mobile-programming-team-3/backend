from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password_async,
    hash_refresh_token,
    password_needs_rehash,
    verify_dummy_password_async,
    verify_password_async,
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
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordChangeRequest,
    UserUpdateRequest,
)


def _refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )


async def signup(db: AsyncSession, data: SignupRequest) -> User:
    if await crud_user.get_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )
    if await crud_user.get_by_nickname(db, data.nickname):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 닉네임입니다.",
        )
    try:
        return await crud_user.create(
            db,
            email=data.email,
            password_hash=await hash_password_async(data.password),
            nickname=data.nickname,
            phone=data.phone,
            region_si=data.region_si,
            region_dong=data.region_dong,
        )
    except IntegrityError:
        # 사전 검사와 INSERT 사이의 레이스, 또는 soft-deleted 사용자의 글로벌 email unique 충돌.
        # 닉네임은 partial unique index 라 활성 사용자끼리만 충돌하므로 여기 도달하면 거의 race.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일 또는 닉네임입니다.",
        )


async def login(db: AsyncSession, email: str, password: str) -> LoginResponse:
    user = await crud_user.get_by_email(db, email)
    # 사용자 부재 분기에서도 verify를 수행해 타이밍 누설 차단
    if user is None:
        await verify_dummy_password_async(password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if not await verify_password_async(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    # passlib 의 deprecation 정책상 더 가벼운 cost factor 가 기본이 되었으면 점진적 재해시.
    # verify 가 이미 성공한 평문이 있는 이 시점에서만 안전하게 갱신할 수 있다.
    if password_needs_rehash(user.password_hash):
        user.password_hash = await hash_password_async(password)

    access_token = create_access_token(user.id)
    raw_rt = generate_refresh_token()
    await crud_rt.create(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_rt),
        expires_at=_refresh_expires_at(),
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_rt,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh(db: AsyncSession, data: TokenRefreshRequest) -> TokenRefreshResponse:
    token_record = await crud_rt.get_active_by_hash(
        db, hash_refresh_token(data.refresh_token)
    )
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 refresh token입니다.",
        )

    # refresh token 회전: 기존 폐기 + 신규 발급. 탈취된 토큰을 7일간 유효한 채 두지 않는다.
    new_raw_rt = generate_refresh_token()
    await crud_rt.rotate(
        db,
        old=token_record,
        new_token_hash=hash_refresh_token(new_raw_rt),
        new_expires_at=_refresh_expires_at(),
    )

    access_token = create_access_token(token_record.user_id)
    return TokenRefreshResponse(
        access_token=access_token,
        refresh_token=new_raw_rt,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def logout(db: AsyncSession, data: LogoutRequest) -> None:
    token_record = await crud_rt.get_active_by_hash(
        db, hash_refresh_token(data.refresh_token)
    )
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 refresh token입니다.",
        )
    await crud_rt.revoke(db, token_record)


async def update_profile(db: AsyncSession, user: User, data: UserUpdateRequest) -> User:
    # exclude_unset: 클라이언트가 보내지 않은 필드는 제외.
    # region_si/region_dong은 명시적 null 전송을 "미설정으로 초기화"로 받는다 (api-spec §1.6).
    # 그 외 필드(nickname/phone/profile_image_url)는 null로 비우는 별도 의미가 정의되지 않아 None 무시.
    clearable = {"region_si", "region_dong"}
    raw = data.model_dump(exclude_unset=True)
    fields = {k: v for k, v in raw.items() if v is not None or k in clearable}
    if not fields:
        return user
    new_nickname = fields.get("nickname")
    if new_nickname is not None and new_nickname != user.nickname:
        if await crud_user.get_by_nickname(db, new_nickname):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 닉네임입니다.",
            )
    try:
        return await crud_user.update(db, user, **fields)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 닉네임입니다.",
        )


async def change_password(
    db: AsyncSession, user: User, data: PasswordChangeRequest
) -> None:
    if not await verify_password_async(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    await crud_user.update(
        db, user, password_hash=await hash_password_async(data.new_password)
    )
    # 비밀번호 변경 시 모든 활성 세션 강제 로그아웃 — 비밀번호가 노출됐을 가능성을 차단.
    await crud_rt.revoke_all_for_user(db, user.id)


async def delete_account(
    db: AsyncSession, user: User, data: AccountDeleteRequest
) -> None:
    if not await verify_password_async(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
        )
    await crud_user.soft_delete(db, user)
    await crud_rt.revoke_all_for_user(db, user.id)
