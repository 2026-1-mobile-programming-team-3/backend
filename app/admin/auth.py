import hmac

import redis.asyncio as aioredis
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings


def _client_ip(request: Request) -> str:
    """프록시 헤더 우선, 없으면 client.host."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _lock_key(ip: str) -> str:
    return f"admin:login:fail:{ip}"


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        super().__init__(secret_key=secret_key)
        # Redis 연결은 단일 인스턴스 재사용 (Starlette/SQLAdmin이 백엔드를 싱글턴으로 보유).
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def login(self, request: Request) -> bool:
        ip = _client_ip(request)
        key = _lock_key(ip)

        # 잠금 상태인지 먼저 확인
        try:
            attempts_raw = await self._redis.get(key)
            attempts = int(attempts_raw) if attempts_raw else 0
        except Exception:
            attempts = 0

        if attempts >= settings.ADMIN_LOGIN_MAX_ATTEMPTS:
            return False

        form = await request.form()
        username_ok = hmac.compare_digest(
            str(form.get("username") or ""), settings.ADMIN_USERNAME
        )
        password_ok = hmac.compare_digest(
            str(form.get("password") or ""), settings.ADMIN_PASSWORD
        )
        if username_ok and password_ok:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
            request.session.update({"admin": True})
            return True

        # 실패 카운트 증가 + TTL 갱신
        try:
            new_count = await self._redis.incr(key)
            if new_count == 1:
                await self._redis.expire(key, settings.ADMIN_LOGIN_LOCKOUT_SECONDS)
            elif new_count >= settings.ADMIN_LOGIN_MAX_ATTEMPTS:
                # 잠금 시점에 TTL 재설정 — 추가 시도가 들어와도 쿨다운 유지
                await self._redis.expire(key, settings.ADMIN_LOGIN_LOCKOUT_SECONDS)
        except Exception:
            pass
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        return request.session.get("admin", False)
