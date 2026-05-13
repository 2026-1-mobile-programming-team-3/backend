from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ws_manager import ws_manager
from app.crud import block as block_crud
from app.crud import chat as chat_crud
from app.crud import match as match_crud
from app.models.enums import ApplicationStatus, NotificationCategory
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreatedResponse,
    ChatMessageItem,
    ChatMessageListResponse,
    ChatThreadApplicant,
    ChatThreadItem,
    ChatThreadListResponse,
)
from app.services import notification as notification_service

_PARTICIPANT_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="채팅 참여자가 아닙니다.",
)
_BLOCKED_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="차단된 상대와는 채팅할 수 없습니다.",
)
_INACTIVE_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="비활성 상태의 신청에는 메시지를 보낼 수 없습니다.",
)


async def _ensure_participant(
    db: AsyncSession,
    *,
    application_id: int,
    user_id: int,
    require_active: bool,
    require_not_blocked: bool,
) -> tuple[int, int, ApplicationStatus, int]:
    """(author_id, applicant_id, app_status, match_id) 반환. 위반 시 HTTPException."""
    info = await chat_crud.get_application_participants(db, application_id)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 신청을 찾을 수 없습니다.",
        )
    author_id, applicant_id, app_status, match_id = info
    if user_id not in (author_id, applicant_id):
        raise _PARTICIPANT_ERROR
    if require_active and app_status not in (
        ApplicationStatus.PENDING,
        ApplicationStatus.ACCEPTED,
    ):
        raise _INACTIVE_ERROR
    if require_not_blocked:
        excluded = await block_crud.list_two_way_excluded_ids(db, user_id)
        opponent = applicant_id if user_id == author_id else author_id
        if opponent in excluded:
            raise _BLOCKED_ERROR
    return author_id, applicant_id, app_status, match_id


async def send_message(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    application_id: int,
    content: str,
) -> ChatMessageCreatedResponse:
    author_id, applicant_id, _, real_match_id = await _ensure_participant(
        db,
        application_id=application_id,
        user_id=current_user.id,
        require_active=True,
        require_not_blocked=True,
    )
    if real_match_id != match_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="매칭과 신청이 일치하지 않습니다.",
        )

    room = await chat_crud.get_or_create_room(db, application_id)
    message = await chat_crud.create_message(
        db,
        chat_room_id=room.id,
        sender_id=current_user.id,
        content=content,
    )

    # 상대방에게 알림 적재 (FCM 실제 발송은 후속).
    opponent_id = applicant_id if current_user.id == author_id else author_id
    await notification_service.enqueue(
        db,
        user_id=opponent_id,
        category=NotificationCategory.MATCH,
        title="새 메시지가 도착했습니다",
        body=content[:80],
        link=f"/matches/{match_id}/applications/{application_id}/chat",
    )
    await db.commit()

    payload = {
        "type": "message.created",
        "id": message.id,
        "room_id": room.id,
        "application_id": application_id,
        "sender_id": current_user.id,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }
    await ws_manager.broadcast(application_id, payload)

    return ChatMessageCreatedResponse(
        id=message.id,
        content=message.content,
        sender_id=message.sender_id,
        created_at=message.created_at,
    )


async def list_messages(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    application_id: int,
    before_id: int | None,
    size: int,
) -> ChatMessageListResponse:
    author_id, applicant_id, _, real_match_id = await _ensure_participant(
        db,
        application_id=application_id,
        user_id=current_user.id,
        require_active=False,  # REJECTED 이후에도 과거 메시지 열람 허용
        require_not_blocked=False,
    )
    if real_match_id != match_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="매칭과 신청이 일치하지 않습니다.",
        )

    room = await chat_crud.get_room_by_application_id(db, application_id)
    if room is None:
        return ChatMessageListResponse(
            items=[], has_more=False, opponent_last_read_at=None
        )

    messages, has_more = await chat_crud.list_messages(
        db, chat_room_id=room.id, before_id=before_id, size=size
    )

    # 본인이 보낸 게 아닌 안 읽은 메시지를 일괄 read 처리.
    changed = await chat_crud.mark_room_messages_read(
        db, chat_room_id=room.id, reader_id=current_user.id
    )
    if changed:
        await db.commit()

    opponent_read = await chat_crud.opponent_last_read_at(
        db, chat_room_id=room.id, viewer_id=current_user.id
    )

    return ChatMessageListResponse(
        items=[
            ChatMessageItem(
                id=m.id,
                content=m.content,
                sender_id=m.sender_id,
                created_at=m.created_at,
            )
            for m in messages
        ],
        has_more=has_more,
        opponent_last_read_at=opponent_read,
    )


async def list_threads(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
) -> ChatThreadListResponse:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="작성자만 스레드 목록을 볼 수 있습니다.",
        )

    excluded = await block_crud.list_two_way_excluded_ids(db, current_user.id)
    rows = await chat_crud.list_threads_for_author(
        db,
        match_id=match_id,
        viewer_id=current_user.id,
        exclude_applicant_ids=excluded or None,
    )
    items = [
        ChatThreadItem(
            application_id=r["application_id"],
            applicant=ChatThreadApplicant(
                id=r["applicant_id"],
                nickname=r["applicant_nickname"],
            ),
            last_message=r["last_message"],
            last_message_at=r["last_message_at"],
            unread_count=r["unread_count"],
            application_status=r["application_status"],
        )
        for r in rows
    ]
    return ChatThreadListResponse(items=items)


# ─── WebSocket 핸들러 보조 ───────────────────────────────────────────────────


async def authorize_ws_participant(
    db: AsyncSession,
    *,
    user_id: int,
    application_id: int,
) -> tuple[bool, str]:
    """(허용 여부, 사유). 사유는 close code 결정용 — 'auth'/'forbidden'."""
    info = await chat_crud.get_application_participants(db, application_id)
    if info is None:
        return False, "forbidden"
    author_id, applicant_id, app_status, _ = info
    if user_id not in (author_id, applicant_id):
        return False, "forbidden"
    if app_status not in (ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED):
        return False, "forbidden"
    excluded = await block_crud.list_two_way_excluded_ids(db, user_id)
    opponent = applicant_id if user_id == author_id else author_id
    if opponent in excluded:
        return False, "forbidden"
    return True, "ok"
