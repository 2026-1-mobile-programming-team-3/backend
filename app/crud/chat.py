from datetime import datetime, timezone

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApplicationStatus
from app.models.match import ChatMessage, ChatRoom, Match, MatchApplication
from app.models.user import User


# ─── ChatRoom ────────────────────────────────────────────────────────────────


async def get_room_by_application_id(
    db: AsyncSession, application_id: int
) -> ChatRoom | None:
    stmt = select(ChatRoom).where(ChatRoom.application_id == application_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_room_by_id(db: AsyncSession, room_id: int) -> ChatRoom | None:
    stmt = select(ChatRoom).where(ChatRoom.id == room_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_or_create_room(
    db: AsyncSession, application_id: int
) -> ChatRoom:
    room = await get_room_by_application_id(db, application_id)
    if room is not None:
        return room
    room = ChatRoom(application_id=application_id)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


# ─── ChatMessage ─────────────────────────────────────────────────────────────


async def create_message(
    db: AsyncSession,
    *,
    chat_room_id: int,
    sender_id: int,
    content: str,
) -> ChatMessage:
    message = ChatMessage(
        chat_room_id=chat_room_id,
        sender_id=sender_id,
        content=content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(
    db: AsyncSession,
    *,
    chat_room_id: int,
    before_id: int | None,
    size: int,
) -> tuple[list[ChatMessage], bool]:
    """created_at DESC 커서 페이지네이션. 다음 페이지 존재 여부와 함께 반환."""
    filters = [ChatMessage.chat_room_id == chat_room_id]
    if before_id is not None:
        filters.append(ChatMessage.id < before_id)
    stmt = (
        select(ChatMessage)
        .where(*filters)
        .order_by(desc(ChatMessage.id))
        .limit(size + 1)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > size
    if has_more:
        rows = rows[:size]
    return rows, has_more


async def mark_room_messages_read(
    db: AsyncSession,
    *,
    chat_room_id: int,
    reader_id: int,
) -> int:
    """reader_id가 보낸 게 아닌 안 읽은 메시지의 read_at = NOW(). commit은 호출자 책임."""
    stmt = (
        update(ChatMessage)
        .where(
            ChatMessage.chat_room_id == chat_room_id,
            ChatMessage.sender_id != reader_id,
            ChatMessage.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    return int(result.rowcount or 0)


async def opponent_last_read_at(
    db: AsyncSession,
    *,
    chat_room_id: int,
    viewer_id: int,
) -> datetime | None:
    """viewer가 보낸 메시지 중 가장 마지막으로 read_at 설정된 시간 — 상대방이 어디까지 읽었는지."""
    stmt = (
        select(func.max(ChatMessage.read_at))
        .where(
            ChatMessage.chat_room_id == chat_room_id,
            ChatMessage.sender_id == viewer_id,
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def unread_count(
    db: AsyncSession,
    *,
    chat_room_id: int,
    viewer_id: int,
) -> int:
    stmt = (
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.chat_room_id == chat_room_id,
            ChatMessage.sender_id != viewer_id,
            ChatMessage.read_at.is_(None),
        )
    )
    return int((await db.execute(stmt)).scalar_one())


# ─── 스레드 목록 (작성자 시점) ───────────────────────────────────────────────


async def list_threads_for_author(
    db: AsyncSession,
    *,
    match_id: int,
    viewer_id: int,
    exclude_applicant_ids: list[int] | None = None,
) -> list[dict]:
    """매칭의 신청자별 스레드 미리보기.
    [{application_id, applicant_id, applicant_nickname, application_status, room_id|None, last_message, last_message_at, unread_count}]
    """
    filters = [MatchApplication.match_id == match_id]
    if exclude_applicant_ids:
        filters.append(MatchApplication.applicant_id.notin_(exclude_applicant_ids))

    # application + applicant nickname + chat_room.id
    stmt = (
        select(
            MatchApplication.id.label("application_id"),
            MatchApplication.applicant_id,
            User.nickname,
            MatchApplication.status,
            ChatRoom.id.label("room_id"),
        )
        .join(
            User,
            and_(User.id == MatchApplication.applicant_id, User.deleted_at.is_(None)),
            isouter=True,
        )
        .join(ChatRoom, ChatRoom.application_id == MatchApplication.id, isouter=True)
        .where(*filters)
        .order_by(MatchApplication.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    results: list[dict] = []
    for r in rows:
        room_id = r.room_id
        last_message: str | None = None
        last_message_at: datetime | None = None
        unread = 0
        if room_id is not None:
            last_stmt = (
                select(ChatMessage.content, ChatMessage.created_at)
                .where(ChatMessage.chat_room_id == room_id)
                .order_by(desc(ChatMessage.id))
                .limit(1)
            )
            last_row = (await db.execute(last_stmt)).first()
            if last_row is not None:
                last_message = last_row[0]
                last_message_at = last_row[1]
            unread = await unread_count(
                db, chat_room_id=room_id, viewer_id=viewer_id
            )
        results.append(
            {
                "application_id": r.application_id,
                "applicant_id": r.applicant_id,
                "applicant_nickname": r.nickname,
                "application_status": r.status,
                "room_id": room_id,
                "last_message": last_message,
                "last_message_at": last_message_at,
                "unread_count": unread,
            }
        )
    return results


# ─── 권한 헬퍼: room 참여자 확인 ─────────────────────────────────────────────


async def get_room_participants(
    db: AsyncSession, chat_room_id: int
) -> tuple[int, int] | None:
    """(author_id, applicant_id) 또는 방이 없으면 None.
    application/match가 삭제된 경우도 None."""
    stmt = (
        select(Match.author_id, MatchApplication.applicant_id, MatchApplication.status)
        .select_from(ChatRoom)
        .join(MatchApplication, MatchApplication.id == ChatRoom.application_id)
        .join(Match, Match.id == MatchApplication.match_id)
        .where(
            ChatRoom.id == chat_room_id,
            Match.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return row[0], row[1]


async def unread_count_for_matches(
    db: AsyncSession,
    *,
    match_ids: list[int],
    viewer_id: int,
) -> dict[int, int]:
    """match_id → 그 매칭의 모든 채팅방 합산 미읽음(viewer가 받은) 메시지 수."""
    if not match_ids:
        return {}
    stmt = (
        select(MatchApplication.match_id, func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatRoom, ChatRoom.id == ChatMessage.chat_room_id)
        .join(MatchApplication, MatchApplication.id == ChatRoom.application_id)
        .where(
            MatchApplication.match_id.in_(match_ids),
            ChatMessage.sender_id != viewer_id,
            ChatMessage.read_at.is_(None),
        )
        .group_by(MatchApplication.match_id)
    )
    return {row[0]: int(row[1]) for row in (await db.execute(stmt)).all()}


async def get_application_participants(
    db: AsyncSession, application_id: int
) -> tuple[int, int, ApplicationStatus, int] | None:
    """(author_id, applicant_id, application_status, match_id) 또는 None."""
    stmt = (
        select(
            Match.author_id,
            MatchApplication.applicant_id,
            MatchApplication.status,
            Match.id,
        )
        .select_from(MatchApplication)
        .join(Match, Match.id == MatchApplication.match_id)
        .where(
            MatchApplication.id == application_id,
            Match.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return row[0], row[1], row[2], row[3]
