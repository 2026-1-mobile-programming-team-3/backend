from datetime import date as date_type

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import match as match_crud
from app.crud import pet as pet_crud
from app.models.enums import ApplicationStatus, MatchStatus
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.match import (
    ApplicationActionRequest,
    ApplicationActionResponse,
    ApplicationApplicantInfo,
    ApplicationCreatedResponse,
    ApplicationCreateRequest,
    ApplicationListItem,
    ApplicationListResponse,
    MatchAuthorSummary,
    MatchCreatedResponse,
    MatchCreateRequest,
    MatchDetail,
    MatchListItem,
    MatchListResponse,
    MatchPetSummary,
    MatchUpdateRequest,
    VolunteerLocationItem,
    VolunteerLocationListResponse,
    VolunteerStatsResponse,
)

_DELETED_USER_NICKNAME = "(탈퇴한 사용자)"


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


# ─── 3.1 POST /matches ───────────────────────────────────────────────────────


async def create_match(
    db: AsyncSession,
    *,
    current_user_id: int,
    data: MatchCreateRequest,
) -> MatchCreatedResponse:
    if data.pet_id is not None:
        pet = await pet_crud.get_by_id(db, data.pet_id)
        if pet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 반려동물을 찾을 수 없습니다.",
            )
        if pet.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 반려동물만 등록할 수 있습니다.",
            )

    match = await match_crud.create_match(
        db,
        author_id=current_user_id,
        title=data.title,
        content=data.content,
        lat=data.latitude,
        lng=data.longitude,
        address=data.address,
        desired_date=data.desired_date,
        pet_id=data.pet_id,
    )
    return MatchCreatedResponse(
        match_id=match.id,
        status=match.status,
        created_at=match.created_at,
    )


# ─── 3.4 GET /matches ────────────────────────────────────────────────────────


async def list_matches(
    db: AsyncSession,
    *,
    status_filter: MatchStatus | None,
    region: str | None,
    from_date: date_type | None,
    to_date: date_type | None,
    page: int,
    size: int,
) -> MatchListResponse:
    rows, total = await match_crud.list_matches(
        db,
        status=status_filter,
        region=region,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )
    items = [
        MatchListItem(
            match_id=m.id,
            title=m.title,
            address=m.address,
            latitude=lat,
            longitude=lng,
            desired_date=m.desired_date,
            status=m.status,
            author_nickname=nickname,
            created_at=m.created_at,
        )
        for m, lat, lng, nickname in rows
    ]
    return MatchListResponse(items=items, total=total, page=page, size=size)


# ─── 3.5 GET /matches/{match_id} ─────────────────────────────────────────────


async def get_match_detail(db: AsyncSession, match_id: int) -> MatchDetail:
    row = await match_crud.get_match_with_relations(db, match_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    match, lat, lng, author, pet = row
    applications_count = await match_crud.count_applications(db, match_id)

    author_summary = MatchAuthorSummary(
        user_id=match.author_id,
        nickname=author.nickname if author and author.deleted_at is None else None,
    )
    pet_summary = (
        MatchPetSummary(
            pet_id=pet.id,
            name=pet.name,
            species=pet.species,
            is_neutered=pet.is_neutered,
        )
        if pet is not None
        else None
    )

    return MatchDetail(
        match_id=match.id,
        author=author_summary,
        pet=pet_summary,
        title=match.title,
        content=match.content,
        address=match.address,
        latitude=lat,
        longitude=lng,
        desired_date=match.desired_date,
        status=match.status,
        applications_count=applications_count,
        created_at=match.created_at,
    )


# ─── 3.6 POST /matches/{match_id}/applications ───────────────────────────────


async def create_application(
    db: AsyncSession,
    *,
    current_user_id: int,
    match_id: int,
    data: ApplicationCreateRequest,
) -> ApplicationCreatedResponse:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 작성한 매칭 요청에는 신청할 수 없습니다.",
        )
    if match.status != MatchStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 진행 중이거나 종료된 매칭입니다.",
        )

    try:
        application = await match_crud.create_application(
            db,
            match_id=match_id,
            applicant_id=current_user_id,
            message=data.message,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신청한 매칭입니다.",
        )

    return ApplicationCreatedResponse(
        application_id=application.id,
        match_id=application.match_id,
        applicant_id=application.applicant_id,
        status=application.status,
        created_at=application.created_at,
    )


# ─── 3.7 GET /matches/{match_id}/applications ────────────────────────────────


async def list_applications(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    page: int,
    size: int,
) -> ApplicationListResponse:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="작성자만 신청자 목록을 볼 수 있습니다.",
        )
    # 작성자가 차단한 사용자의 신청은 노출하지 않는다 (가시성 정책 일관).
    from app.crud import block as block_crud  # lazy import
    blocked_ids = await block_crud.list_blocked_ids(db, current_user.id)

    rows, total = await match_crud.list_applications_with_applicants(
        db, match_id, page=page, size=size, exclude_applicant_ids=blocked_ids or None
    )
    items = [
        ApplicationListItem(
            application_id=app.id,
            applicant=ApplicationApplicantInfo(
                applicant_id=app.applicant_id,
                nickname=nickname if nickname is not None else _DELETED_USER_NICKNAME,
            ),
            message=app.message,
            status=app.status,
            created_at=app.created_at,
        )
        for app, nickname in rows
    ]
    return ApplicationListResponse(items=items, total=total, page=page, size=size)


# ─── 3.8 PATCH /matches/{match_id}/applications/{application_id} ─────────────


async def respond_application(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    application_id: int,
    data: ApplicationActionRequest,
) -> ApplicationActionResponse:
    # 동시 ACCEPT 레이스 차단: 매칭과 대상 신청을 트랜잭션 내에서 row-lock.
    match = await match_crud.get_match_active(db, match_id, for_update=True)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="작성자만 신청을 처리할 수 있습니다.",
        )

    application = await match_crud.get_application(db, application_id, for_update=True)
    if application is None or application.match_id != match_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 신청을 찾을 수 없습니다.",
        )
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리된 신청입니다.",
        )

    if data.action == "ACCEPT":
        if match.status != MatchStatus.WAITING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 진행 중이거나 종료된 매칭입니다.",
            )
        await match_crud.accept_application(
            db, match=match, application=application
        )
    else:
        await match_crud.reject_application(db, application)

    await db.commit()
    await db.refresh(application)
    await db.refresh(match)

    return ApplicationActionResponse(
        application_id=application.id,
        status=application.status,
        match_status=match.status,
    )


# ─── 3.2 PATCH /matches/{match_id} ───────────────────────────────────────────

_EDITABLE_MATCH_STATUSES = (MatchStatus.WAITING, MatchStatus.MATCHING)


async def update_match(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    data: MatchUpdateRequest,
) -> MessageResponse:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 작성한 매칭 요청만 수정할 수 있습니다.",
        )
    if match.status not in _EDITABLE_MATCH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 진행 중이거나 완료된 매칭은 수정할 수 없습니다.",
        )

    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return MessageResponse(message="변경 사항 없음")

    if fields.get("pet_id") is not None:
        pet = await pet_crud.get_by_id(db, fields["pet_id"])
        if pet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 반려동물을 찾을 수 없습니다.",
            )
        if pet.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 반려동물만 등록할 수 있습니다.",
            )

    await match_crud.update_match(db, match, **fields)
    await db.commit()
    return MessageResponse(message="성공적으로 처리되었습니다.")


# ─── 3.3 DELETE /matches/{match_id} ──────────────────────────────────────────


async def delete_match(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
) -> None:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 작성한 매칭 요청만 삭제할 수 있습니다.",
        )
    if match.status not in _EDITABLE_MATCH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 진행 중이거나 완료된 매칭은 삭제할 수 없습니다.",
        )

    await match_crud.soft_delete_match(db, match)
    await db.commit()


# ─── 3.14 GET /users/me/volunteer-stats ──────────────────────────────────────


async def get_volunteer_stats(
    db: AsyncSession,
    *,
    user_id: int,
) -> VolunteerStatsResponse:
    total_count = await match_crud.count_completed_volunteer_matches(db, user_id)
    avg_rating = await match_crud.avg_review_rating_for(db, user_id)
    # total_hours: 봉사 시간 추적 컬럼이 아직 없어 0.0으로 고정. 추후 활동 로그 추가 시 보강.
    return VolunteerStatsResponse(
        total_count=total_count,
        total_hours=0.0,
        avg_rating=avg_rating,
    )
