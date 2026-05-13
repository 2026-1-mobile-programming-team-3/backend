from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.geo import ReverseGeocodeResponse
from app.services import geo as geo_service

router = APIRouter(prefix="/geo", tags=["Geo"])


@router.get("/reverse", response_model=ReverseGeocodeResponse)
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    _user: User = Depends(get_current_user),
):
    """좌표 → 행정구역. 인증 필요. 시흥시 내부면 동 이름만, 외부면 '동 (시흥시 외부)' 라벨."""
    return await geo_service.reverse_geocode(lat, lng)
