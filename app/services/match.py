from datetime import date as date_type

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import block as block_crud
from app.crud import match as match_crud
from app.crud import pet as pet_crud
from app.models.enums import (
    ApplicationStatus,
    MatchStatus,
    NotificationCategory,
)
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
    MatchReviewCreatedResponse,
    MatchReviewCreateRequest,
    MatchStatusUpdateRequest,
    MatchStatusUpdateResponse,
    MatchUpdateRequest,
    MyMatchListItem,
    MyMatchListResponse,
    VolunteerLocationItem,
    VolunteerLocationListResponse,
    VolunteerStatsResponse,
)
from app.services import notification as notification_service

_DELETED_USER_NICKNAME = "(탈퇴한 사용자)"


async def list_volunteer_locations(
    db: AsyncSession, *, current_user: User
) -> VolunteerLocationListResponse:
    excluded = await block_crud.list_two_way_excluded_ids(db, current_user.id)
    rows = await match_crud.list_waiting_matches(
        db, exclude_author_ids=excluded or None
    )
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
        desired_time=data.desired_time,
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
    current_user: User,
    status_filter: MatchStatus | None,
    region: str | None,
    from_date: date_type | None,
    to_date: date_type | None,
    page: int,
    size: int,
) -> MatchListResponse:
    excluded = await block_crud.list_two_way_excluded_ids(db, current_user.id)
    rows, total = await match_crud.list_matches(
        db,
        status=status_filter,
        region=region,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
        exclude_author_ids=excluded or None,
    )
    items = [
        MatchListItem(
            match_id=m.id,
            title=m.title,
            address=m.address,
            latitude=lat,
            longitude=lng,
            desired_date=m.desired_date,
            desired_time=m.desired_time,
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
        desired_time=match.desired_time,
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

    # 매칭 작성자에게 신청 도착 알림.
    await notification_service.enqueue(
        db,
        user_id=match.author_id,
        category=NotificationCategory.VOLUNTEER,
        title="새 봉사 신청이 도착했습니다",
        body=f"'{match.title}'에 봉사 신청이 들어왔습니다.",
        link=f"/matches/{match.id}/applications",
    )
    await db.commit()

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
        rows, total = await match_crud.list_applications_with_applicants(
            db, match_id, page=page, size=size, applicant_id=current_user.id
        )
    else:
        # 작성자가 차단한 사용자의 신청은 노출하지 않는다 (가시성 정책 일관).
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
        await notification_service.enqueue(
            db,
            user_id=application.applicant_id,
            category=NotificationCategory.VOLUNTEER,
            title="봉사 신청이 수락되었습니다",
            body=f"'{match.title}' 매칭이 진행됩니다.",
            link=f"/matches/{match.id}",
        )
    else:
        await match_crud.reject_application(db, application)
        await notification_service.enqueue(
            db,
            user_id=application.applicant_id,
            category=NotificationCategory.VOLUNTEER,
            title="봉사 신청이 거절되었습니다",
            body=f"'{match.title}' 매칭의 신청이 거절되었습니다.",
            link=f"/matches/{match.id}",
        )

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


# ─── 3.9 PATCH /matches/{match_id}/status ────────────────────────────────────


async def update_match_status(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    data: MatchStatusUpdateRequest,
) -> MatchStatusUpdateResponse:
    match = await match_crud.get_match_active(db, match_id, for_update=True)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="작성자만 상태를 변경할 수 있습니다.",
        )

    target = MatchStatus(data.status)

    if target == MatchStatus.PROGRESS:
        if match.status == MatchStatus.PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 진행 중인 매칭입니다.",
            )
        if match.status == MatchStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 완료된 매칭입니다.",
            )
        has_accepted = await match_crud.has_accepted_application(db, match.id)
        if not has_accepted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="수락된 신청이 있어야 진행 상태로 전이할 수 있습니다.",
            )
        await match_crud.set_match_status(db, match, MatchStatus.PROGRESS)
    elif target == MatchStatus.DONE:
        if match.status != MatchStatus.PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="진행 중인 매칭만 완료 처리할 수 있습니다.",
            )
        await match_crud.set_match_status(db, match, MatchStatus.DONE)
        applicant_id = await match_crud.get_accepted_applicant_id(db, match.id)
        if applicant_id is not None:
            await notification_service.enqueue(
                db,
                user_id=applicant_id,
                category=NotificationCategory.MATCH,
                title="매칭이 완료되었습니다",
                body=f"'{match.title}' 매칭이 완료 처리되었습니다.",
                link=f"/matches/{match.id}",
            )

    await db.commit()
    await db.refresh(match)
    return MatchStatusUpdateResponse(
        match_id=match.id,
        status=match.status,
        updated_at=match.updated_at,
    )


# ─── 3.13 POST /matches/{match_id}/review ────────────────────────────────────


async def create_review(
    db: AsyncSession,
    *,
    current_user: User,
    match_id: int,
    data: MatchReviewCreateRequest,
) -> MatchReviewCreatedResponse:
    match = await match_crud.get_match_active(db, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 매칭 요청을 찾을 수 없습니다.",
        )
    if match.status != MatchStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="완료된 매칭에서만 후기를 작성할 수 있습니다.",
        )

    accepted_applicant_id = await match_crud.get_accepted_applicant_id(db, match.id)
    is_author = current_user.id == match.author_id
    is_applicant = (
        accepted_applicant_id is not None
        and current_user.id == accepted_applicant_id
    )
    if not (is_author or is_applicant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="매칭 참여자만 후기를 작성할 수 있습니다.",
        )

    if is_author:
        reviewee_id = accepted_applicant_id
    else:
        reviewee_id = match.author_id

    if reviewee_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="후기 대상자를 확정할 수 없습니다.",
        )

    try:
        review = await match_crud.create_review(
            db,
            match_id=match.id,
            reviewer_id=current_user.id,
            reviewee_id=reviewee_id,
            rating=data.rating,
            content=data.content,
            proof_image_urls=data.proof_image_urls,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 후기를 작성하였습니다.",
        )

    await notification_service.enqueue(
        db,
        user_id=reviewee_id,
        category=NotificationCategory.REVIEW,
        title="새 후기가 등록되었습니다",
        body=f"'{match.title}' 매칭에 후기가 등록되었습니다.",
        link=f"/matches/{match.id}",
    )
    await db.commit()

    return MatchReviewCreatedResponse(
        review_id=review.id,
        match_id=match.id,
        rating=review.rating,
        created_at=review.created_at,
    )


# ─── 3.15 GET /users/me/matches ──────────────────────────────────────────────


async def list_my_matches(
    db: AsyncSession,
    *,
    current_user: User,
    role: str,
    status_filter: MatchStatus | None,
    page: int,
    size: int,
) -> MyMatchListResponse:
    from app.crud import chat as chat_crud

    if role == "author":
        rows, total = await match_crud.list_my_matches_as_author(
            db,
            user_id=current_user.id,
            status_filter=status_filter,
            page=page,
            size=size,
        )
        match_ids = [m.id for m, *_ in rows]
        # 매칭별 ACCEPTED 봉사자 닉네임 + 미읽음 메시지 수 (일괄 조회로 N+1 방지).
        matched_map = await match_crud.matched_applicant_nicknames(db, match_ids)
        unread_map = await chat_crud.unread_count_for_matches(
            db, match_ids=match_ids, viewer_id=current_user.id
        )
        items = [
            MyMatchListItem(
                match_id=m.id,
                title=m.title,
                address=m.address,
                latitude=lat,
                longitude=lng,
                desired_date=m.desired_date,
                desired_time=m.desired_time,
                status=m.status,
                author_nickname=author_nick,
                created_at=m.created_at,
                applications_count=app_count,
                matched_applicant_nickname=matched_map.get(m.id),
                unread_message_count=unread_map.get(m.id, 0),
                my_application_status=None,
                received_rating=None,
            )
            for m, lat, lng, author_nick, app_count in rows
        ]
    elif role == "applicant":
        rows, total = await match_crud.list_my_matches_as_applicant(
            db,
            user_id=current_user.id,
            status_filter=status_filter,
            page=page,
            size=size,
        )
        match_ids = [m.id for m, *_ in rows]
        # 본인이 reviewee로 받은 후기 평점 (DONE 매칭 카드의 '받은 평점' 표시용).
        rating_map = await match_crud.received_ratings_for(
            db, user_id=current_user.id, match_ids=match_ids
        )
        items = [
            MyMatchListItem(
                match_id=m.id,
                title=m.title,
                address=m.address,
                latitude=lat,
                longitude=lng,
                desired_date=m.desired_date,
                desired_time=m.desired_time,
                status=m.status,
                author_nickname=author_nick,
                created_at=m.created_at,
                applications_count=None,
                matched_applicant_nickname=None,
                unread_message_count=0,
                my_application_status=my_status,
                received_rating=rating_map.get(m.id),
            )
            for m, lat, lng, author_nick, my_status in rows
        ]
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role 은 'author' 또는 'applicant' 이어야 합니다.",
        )

    return MyMatchListResponse(items=items, total=total, page=page, size=size)
