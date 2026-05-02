from datetime import date as date_type
from datetime import datetime, timezone

from geoalchemy2 import Geography, Geometry
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.enums import ApplicationStatus, MatchStatus
from app.models.match import Match, MatchApplication, MatchReview
from app.models.user import Pet, User


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


# ─── Match CRUD ──────────────────────────────────────────────────────────────


async def create_match(
    db: AsyncSession,
    *,
    author_id: int,
    title: str,
    content: str,
    lat: float,
    lng: float,
    address: str | None,
    desired_date: date_type | None,
    pet_id: int | None,
) -> Match:
    match = Match(
        author_id=author_id,
        pet_id=pet_id,
        title=title,
        content=content,
        location=func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography),
        address=address,
        desired_date=desired_date,
        status=MatchStatus.WAITING,
    )
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return match


async def get_match_active(db: AsyncSession, match_id: int) -> Match | None:
    """deleted_at IS NULL 인 매칭만 반환. 상태 무관."""
    stmt = select(Match).where(
        Match.id == match_id,
        Match.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_match_with_relations(
    db: AsyncSession, match_id: int
) -> tuple[Match, float, float, User | None, Pet | None] | None:
    """(Match, lat, lng, author, pet) — deleted_at IS NULL 만 반환."""
    location_geom = func.cast(Match.location, Geometry)
    stmt = (
        select(
            Match,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
            User,
            Pet,
        )
        .outerjoin(User, User.id == Match.author_id)
        .outerjoin(Pet, Pet.id == Match.pet_id)
        .where(Match.id == match_id, Match.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return (row[0], float(row[1]), float(row[2]), row[3], row[4])


async def list_matches(
    db: AsyncSession,
    *,
    status: MatchStatus | None,
    region: str | None,
    from_date: date_type | None,
    to_date: date_type | None,
    page: int,
    size: int,
) -> tuple[list[tuple[Match, float, float, str | None]], int]:
    """필터 적용한 (Match, lat, lng, author_nickname) 페이지 + 총 개수.
    deleted_at IS NULL 매칭만. created_at DESC."""
    location_geom = func.cast(Match.location, Geometry)

    base_filters = [Match.deleted_at.is_(None)]
    if status is not None:
        base_filters.append(Match.status == status)
    if region:
        base_filters.append(Match.address.ilike(f"%{region}%"))
    if from_date is not None:
        base_filters.append(Match.desired_date >= from_date)
    if to_date is not None:
        base_filters.append(Match.desired_date <= to_date)

    count_stmt = select(func.count()).select_from(Match).where(*base_filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(
            Match,
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
            User.nickname,
        )
        .outerjoin(User, (User.id == Match.author_id) & (User.deleted_at.is_(None)))
        .where(*base_filters)
        .order_by(Match.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    rows = [
        (row[0], float(row[1]), float(row[2]), row[3]) for row in result.all()
    ]
    return rows, int(total)


async def soft_delete_match(db: AsyncSession, match: Match) -> None:
    """deleted_at = NOW(). commit은 호출자 책임."""
    match.deleted_at = datetime.now(timezone.utc)


async def update_match(db: AsyncSession, match: Match, **fields) -> Match:
    """부분 업데이트. lat/lng는 둘 다 있을 때만 location 갱신.
    commit은 호출자 책임."""
    lat = fields.pop("latitude", None)
    lng = fields.pop("longitude", None)
    if lat is not None and lng is not None:
        match.location = func.ST_SetSRID(
            func.ST_MakePoint(lng, lat), 4326
        ).cast(Geography)
    for key, value in fields.items():
        setattr(match, key, value)
    match.updated_at = datetime.now(timezone.utc)
    return match


async def count_completed_volunteer_matches(
    db: AsyncSession, user_id: int
) -> int:
    """user_id가 ACCEPTED 봉사자였고 매칭이 DONE인 건수."""
    stmt = (
        select(func.count())
        .select_from(MatchApplication)
        .join(Match, Match.id == MatchApplication.match_id)
        .where(
            MatchApplication.applicant_id == user_id,
            MatchApplication.status == ApplicationStatus.ACCEPTED,
            Match.status == MatchStatus.DONE,
            Match.deleted_at.is_(None),
        )
    )
    return int((await db.execute(stmt)).scalar_one())


async def avg_review_rating_for(
    db: AsyncSession, user_id: int
) -> float | None:
    """user_id가 reviewee인 후기 평점 평균. 없으면 None."""
    stmt = select(func.avg(MatchReview.rating)).where(
        MatchReview.reviewee_id == user_id
    )
    val = (await db.execute(stmt)).scalar_one_or_none()
    return float(val) if val is not None else None


# ─── MatchApplication CRUD ───────────────────────────────────────────────────


async def create_application(
    db: AsyncSession,
    *,
    match_id: int,
    applicant_id: int,
    message: str | None,
) -> MatchApplication:
    """unique(match_id, applicant_id) 위반 시 IntegrityError 발생 — 호출자가 잡아 409 변환."""
    application = MatchApplication(
        match_id=match_id,
        applicant_id=applicant_id,
        message=message,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def list_applications_with_applicants(
    db: AsyncSession, match_id: int
) -> list[tuple[MatchApplication, str | None]]:
    """(application, applicant_nickname) created_at ASC."""
    stmt = (
        select(MatchApplication, User.nickname)
        .outerjoin(
            User,
            (User.id == MatchApplication.applicant_id) & (User.deleted_at.is_(None)),
        )
        .where(MatchApplication.match_id == match_id)
        .order_by(MatchApplication.created_at.asc())
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def count_applications(db: AsyncSession, match_id: int) -> int:
    stmt = select(func.count()).select_from(MatchApplication).where(
        MatchApplication.match_id == match_id
    )
    return int((await db.execute(stmt)).scalar_one())


async def get_application(
    db: AsyncSession, application_id: int
) -> MatchApplication | None:
    stmt = select(MatchApplication).where(MatchApplication.id == application_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def accept_application(
    db: AsyncSession,
    *,
    match: Match,
    application: MatchApplication,
) -> None:
    """대상 application을 ACCEPTED로, 같은 match의 다른 PENDING은 REJECTED로,
    match.status를 PROGRESS로 일괄 갱신. commit은 호출자 책임."""
    now = datetime.now(timezone.utc)

    # 같은 매칭의 다른 PENDING application 일괄 REJECT
    others = await db.execute(
        select(MatchApplication).where(
            MatchApplication.match_id == match.id,
            MatchApplication.id != application.id,
            MatchApplication.status == ApplicationStatus.PENDING,
        )
    )
    for other in others.scalars().all():
        other.status = ApplicationStatus.REJECTED
        other.updated_at = now

    application.status = ApplicationStatus.ACCEPTED
    application.updated_at = now
    match.status = MatchStatus.PROGRESS
    match.updated_at = now


async def reject_application(
    db: AsyncSession, application: MatchApplication
) -> None:
    """단건 REJECT. commit은 호출자 책임."""
    application.status = ApplicationStatus.REJECTED
    application.updated_at = datetime.now(timezone.utc)
