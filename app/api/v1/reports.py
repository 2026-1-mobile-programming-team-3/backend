from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.report import ReportCreatedResponse, ReportCreateRequest
from app.services import report as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    data: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await report_service.create_report(
        db, reporter_id=current_user.id, data=data
    )
