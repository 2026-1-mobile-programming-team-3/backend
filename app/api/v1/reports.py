from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.report import (
    ChatReportCreatedResponse,
    ChatReportCreateRequest,
    ReportCreatedResponse,
    ReportCreateRequest,
)
from app.services import report as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/hour")
async def create_report(
    request: Request,
    data: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await report_service.create_report(
        db, reporter_id=current_user.id, data=data
    )


@router.post(
    "/chat",
    response_model=ChatReportCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/hour")
async def create_chat_report(
    request: Request,
    data: ChatReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await report_service.create_chat_report(
        db, reporter_id=current_user.id, data=data
    )
