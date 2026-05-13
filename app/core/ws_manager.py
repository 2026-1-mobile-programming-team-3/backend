"""인메모리 WebSocket ConnectionManager — application_id별 broadcast 채널.

단일 워커 가정. 멀티 워커 확장 시 broadcast 메서드 내부에 Redis pub/sub 추가.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room_key: int, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(room_key, set()).add(ws)

    async def disconnect(self, room_key: int, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._rooms.get(room_key)
            if conns is None:
                return
            conns.discard(ws)
            if not conns:
                self._rooms.pop(room_key, None)

    async def broadcast(self, room_key: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._rooms.get(room_key, set()))
        if not targets:
            return
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                conns = self._rooms.get(room_key)
                if conns is not None:
                    for ws in dead:
                        conns.discard(ws)
                    if not conns:
                        self._rooms.pop(room_key, None)

    def connection_count(self, room_key: int) -> int:
        return len(self._rooms.get(room_key, set()))


ws_manager = ConnectionManager()
