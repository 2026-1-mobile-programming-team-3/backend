import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal, get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


_redis_client: aioredis.Redis | None = None


def _build_redis_client() -> aioredis.Redis:
    # aioredis.from_url 은 내부적으로 ConnectionPool 을 만든다.
    # 매 요청마다 호출하면 새 풀이 생기므로 반드시 싱글톤으로 재사용해야 한다.
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
        health_check_interval=30,
    )


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = _build_redis_client()
    return _redis_client


async def close_redis() -> None:
    """앱 종료 시 호출. 풀과 connection을 정리한다."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    from app.crud.user import get_by_id

    user = await get_by_id(db, user_id)
    if user is None or user.deleted_at is not None:
        raise credentials_exception
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


async def get_current_volunteer(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (UserRole.VOLUNTEER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="봉사자 권한이 필요합니다.",
        )
    return current_user


# WebSocket은 HTTP 인증 의존성을 그대로 쓸 수 없어 별도 헬퍼.
# query `token` (선호) 또는 첫 subprotocol에 'bearer.<JWT>' 형태를 둘 다 허용한다.
def _extract_ws_token(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if token:
        return token
    for proto in websocket.headers.get_list("sec-websocket-protocol") or []:
        for part in (p.strip() for p in proto.split(",")):
            if part.startswith("bearer."):
                return part[len("bearer.") :]
    return None


async def get_user_from_ws(websocket: WebSocket) -> User | None:
    """WS 핸드쉐이크 단계에서 JWT 디코드 → User 반환. 실패 시 None.
    핸들러가 None을 받으면 4401로 close 해야 한다."""
    token = _extract_ws_token(websocket)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        return None

    from app.crud.user import get_by_id

    async with AsyncSessionLocal() as session:
        user = await get_by_id(session, user_id)
        if user is None or user.deleted_at is not None:
            return None
        return user
