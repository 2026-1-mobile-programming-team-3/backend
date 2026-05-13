import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.home import HomeDashboardResponse
from app.services import home as home_service

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/dashboard", response_model=HomeDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    return await home_service.get_dashboard(
        db, current_user=current_user, redis=redis
    )
