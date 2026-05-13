"""채팅 WebSocket 채널 — /ws/applications/{application_id}.

REST 메시지 송수신은 matches.py 에 있고, 본 라우터는 실시간 broadcast 수신용.
JWT는 query token 또는 sec-websocket-protocol 의 'bearer.<JWT>' 형태로 받는다.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.deps import get_user_from_ws
from app.core.ws_manager import ws_manager
from app.db.session import AsyncSessionLocal
from app.services import chat as chat_service

router = APIRouter(prefix="/ws", tags=["Chat WS"])


@router.websocket("/applications/{application_id}")
async def applications_chat_ws(websocket: WebSocket, application_id: int) -> None:
    user = await get_user_from_ws(websocket)
    if user is None:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as session:
        allowed, reason = await chat_service.authorize_ws_participant(
            session, user_id=user.id, application_id=application_id
        )
    if not allowed:
        await websocket.close(code=4403 if reason == "forbidden" else 4401)
        return

    await websocket.accept()
    await ws_manager.connect(application_id, websocket)
    try:
        while True:
            # 클라이언트 입력은 ping/pong 정도만 받으며 무시한다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(application_id, websocket)
