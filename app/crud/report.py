from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReportType
from app.models.report import Report


async def create_report(
    db: AsyncSession,
    *,
    reporter_id: int,
    target_user_id: int,
    reason: str,
) -> Report:
    """USER 신고. partial unique(reporter, target WHERE report_type='USER') 위반 시 IntegrityError."""
    report = Report(
        reporter_id=reporter_id,
        target_user_id=target_user_id,
        reason=reason,
        report_type=ReportType.USER,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def create_chat_report(
    db: AsyncSession,
    *,
    reporter_id: int,
    target_user_id: int,
    chat_room_id: int,
    message_id: int,
    reason: str,
) -> Report:
    """채팅 메시지 단위 신고 — 메시지마다 자유롭게 작성 가능."""
    report = Report(
        reporter_id=reporter_id,
        target_user_id=target_user_id,
        reason=reason,
        report_type=ReportType.CHAT,
        chat_room_id=chat_room_id,
        message_id=message_id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
