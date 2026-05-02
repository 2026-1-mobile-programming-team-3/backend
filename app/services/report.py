from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import report as report_crud
from app.crud import user as user_crud
from app.schemas.report import ReportCreatedResponse, ReportCreateRequest


async def create_report(
    db: AsyncSession,
    *,
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
