from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import chat as chat_crud
from app.crud import report as report_crud
from app.crud import user as user_crud
from app.models.match import ChatMessage
from app.schemas.report import (
    ChatReportCreatedResponse,
    ChatReportCreateRequest,
    ReportCreatedResponse,
    ReportCreateRequest,
)
from sqlalchemy import select


async def create_report(
    db: AsyncSession,
    reporter_id: int,
    data: ReportCreateRequest,
) -> ReportCreatedResponse:
    if data.target_user_id == reporter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인을 신고할 수 없습니다.",
        )
    target = await user_crud.get_by_id(db, data.target_user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 사용자를 찾을 수 없습니다.",
        )
    try:
        report = await report_crud.create_report(
            db,
            reporter_id=reporter_id,
            target_user_id=data.target_user_id,
            reason=data.reason,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신고한 사용자입니다.",
        )
    return ReportCreatedResponse(
        id=report.id,
        target_user_id=report.target_user_id,
        reason=report.reason,
        created_at=report.created_at,
    )


async def create_chat_report(
    db: AsyncSession,
    *,
    reporter_id: int,
    data: ChatReportCreateRequest,
) -> ChatReportCreatedResponse:
    if data.target_user_id == reporter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인을 신고할 수 없습니다.",
        )

    participants = await chat_crud.get_room_participants(db, data.chat_id)
    if participants is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 채팅방을 찾을 수 없습니다.",
        )
    author_id, applicant_id = participants
    if reporter_id not in (author_id, applicant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="채팅 참여자만 신고할 수 있습니다.",
        )
    opponent = applicant_id if reporter_id == author_id else author_id
    if data.target_user_id != opponent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="해당 채팅방의 상대방만 신고할 수 있습니다.",
        )

    msg_stmt = select(ChatMessage).where(
        ChatMessage.id == data.message_id,
        ChatMessage.chat_room_id == data.chat_id,
    )
    msg = (await db.execute(msg_stmt)).scalar_one_or_none()
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 메시지를 찾을 수 없습니다.",
        )
    if msg.sender_id != data.target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="해당 메시지의 작성자가 아닙니다.",
        )

    report = await report_crud.create_chat_report(
        db,
        reporter_id=reporter_id,
        target_user_id=data.target_user_id,
        chat_room_id=data.chat_id,
        message_id=data.message_id,
        reason=data.reason,
    )
    return ChatReportCreatedResponse(
        report_id=report.id,
        status="RECEIVED",
        created_at=report.created_at,
    )
