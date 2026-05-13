"""Redis JSON 캐시 헬퍼 — get-or-set 패턴."""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

import redis.asyncio as aioredis


async def get_or_set_json(
    redis: aioredis.Redis,
    *,
    key: str,
    ttl_seconds: int,
    factory: Callable[[], Awaitable[Any]],
) -> Any:
    """key 가 있으면 JSON 디코딩해 반환. 없으면 factory() 호출 후 setex 저장."""
    cached = await redis.get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except (TypeError, ValueError):
            pass
    value = await factory()
    await redis.setex(key, ttl_seconds, json.dumps(value, default=str))
    return value
