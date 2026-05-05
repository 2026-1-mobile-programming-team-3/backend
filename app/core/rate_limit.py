from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _key_func(request) -> str:  # type: ignore[no-untyped-def]
    """프록시 헤더 우선, 없으면 client.host."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


# slowapi는 Redis URL을 storage_uri로 직접 받아 분산 카운트가 가능하다.
limiter = Limiter(
    key_func=_key_func,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
)
