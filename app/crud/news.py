from datetime import date

from sqlalchemy import and_, extract, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.news import CalendarEvent


async def get_calendar_events(
    db: AsyncSession,
    year: int,
    month: int,
) -> list[CalendarEvent]:
    """start_date 또는 end_date가 해당 연/월에 걸치는 이벤트를 반환한다."""
    stmt = select(CalendarEvent).where(
        or_(
            and_(
                extract("year", CalendarEvent.start_date) == year,
                extract("month", CalendarEvent.start_date) == month,
            ),
            and_(
                extract("year", CalendarEvent.end_date) == year,
                extract("month", CalendarEvent.end_date) == month,
            ),
        )
    ).order_by(CalendarEvent.start_date)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_daily_events(
    db: AsyncSession,
    target_date: date,
) -> list[CalendarEvent]:
    """start_date <= target_date <= end_date 인 이벤트를 반환한다."""
    stmt = select(CalendarEvent).where(
        and_(
            CalendarEvent.start_date <= target_date,
            CalendarEvent.end_date >= target_date,
        )
    ).order_by(CalendarEvent.start_date, CalendarEvent.event_time)
    result = await db.execute(stmt)
    return list(result.scalars().all())
