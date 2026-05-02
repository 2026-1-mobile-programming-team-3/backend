from geoalchemy2 import Geometry
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.enums import MatchStatus
from app.models.match import Match


async def list_waiting_matches(
    db: AsyncSession,
) -> list[tuple[Match, float, float]]:
    """status=WAITING AND deleted_at IS NULL 매칭의 (Match, lat, lng) 200건. created_at DESC."""
    location_geom = func.cast(Match.location, Geometry)
    stmt = (
        select(
            Match,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
        )
        .where(
            Match.status == MatchStatus.WAITING,
            Match.deleted_at.is_(None),
        )
        .order_by(Match.created_at.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    return [(row[0], float(row[1]), float(row[2])) for row in result.all()]
