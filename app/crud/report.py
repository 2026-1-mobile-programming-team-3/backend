from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


async def create_report(
    db: AsyncSession,
    *,
    reporter_id: int,
    target_user_id: int,
    reason: str,
) -> Report:
    """unique(reporter_id, target_user_id) 위반 시 IntegrityError — 호출자가 잡아 409 변환."""
    report = Report(
        reporter_id=reporter_id,
        target_user_id=target_user_id,
        reason=reason,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
