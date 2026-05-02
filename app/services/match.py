from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import match as match_crud
from app.schemas.match import VolunteerLocationItem, VolunteerLocationListResponse


async def list_volunteer_locations(db: AsyncSession) -> VolunteerLocationListResponse:
    rows = await match_crud.list_waiting_matches(db)
    return VolunteerLocationListResponse(
        volunteer_requests=[
            VolunteerLocationItem(
                request_id=m.id,
                title=m.title,
                latitude=lat,
                longitude=lng,
                status=m.status,
            )
            for m, lat, lng in rows
        ]
    )
