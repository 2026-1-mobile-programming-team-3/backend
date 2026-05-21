from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import store as crud_store
from app.crud import store_request as crud_sr
from app.models.enums import (
    NotificationCategory,
    StoreCategory,
    StoreRequestStatus,
    StoreRequestType,
    StoreStatus,
)
from app.models.store import Store
from app.models.store_request import StoreRequest
from app.schemas.store_request import (
    StoreRequestAdminItem,
    StoreRequestAdminListResponse,
    StoreRequestCreate,
    StoreRequestCreatedResponse,
    StoreRequestItem,
    StoreRequestListResponse,
    StoreRequestProcessedResponse,
)
from app.services import notification as notification_service


def _payload_has_plans(payload: dict) -> bool:
    return "plans" in payload and payload["plans"] is not None


def _serialize_request(req: StoreRequest) -> StoreRequestItem:
    return StoreRequestItem.model_validate(req)


# ─── 사용자측 ─────────────────────────────────────────────────────────────────

async def create_request(
    db: AsyncSession,
    *,
    current_user_id: int,
    data: StoreRequestCreate,
) -> StoreRequestCreatedResponse:
    # mode='json' → enum은 항상 value 문자열로 직렬화. JSONB 저장과 후속 비교 모두 단순해진다.
    payload = data.payload.model_dump(exclude_none=True, mode="json")

    if data.type == StoreRequestType.UPDATE:
        store = await crud_store.get_by_id_for_owner(db, data.target_store_id)
        if (
            store is None
            or store.deleted_at is not None
            or store.status != StoreStatus.APPROVED
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="대상 매장을 찾을 수 없습니다.",
            )
        if store.owner_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인이 점주로 인증된 매장만 수정 요청할 수 있습니다.",
            )
        if _payload_has_plans(payload):
            current_category = (
                store.category.value
                if isinstance(store.category, StoreCategory)
                else store.category
            )
            new_category_value = payload.get("category", current_category)
            if new_category_value != StoreCategory.PET_HOTEL.value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="가격 플랜(plans)은 PET_HOTEL 매장에서만 사용할 수 있습니다.",
                )

    if data.type == StoreRequestType.ADD:
        if (
            _payload_has_plans(payload)
            and payload["category"] != StoreCategory.PET_HOTEL.value
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="가격 플랜(plans)은 PET_HOTEL 매장에서만 사용할 수 있습니다.",
            )

    try:
        req = await crud_sr.create(
            db,
            user_id=current_user_id,
            type_=data.type,
            target_store_id=data.target_store_id,
            payload=payload,
            proof_urls=data.proof_urls,
            message=data.message,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리 대기 중인 동일 요청이 있습니다.",
        )
    return StoreRequestCreatedResponse.model_validate(req)


async def list_my_requests(
    db: AsyncSession,
    *,
    current_user_id: int,
    status_filter: StoreRequestStatus | None,
    page: int,
    size: int,
) -> StoreRequestListResponse:
    rows, total = await crud_sr.list_by_user(
        db,
        current_user_id,
        status_filter=status_filter,
        page=page,
        size=size,
    )
    return StoreRequestListResponse(
        items=[_serialize_request(r) for r in rows],
        total=total,
        page=page,
        size=size,
    )


async def get_my_request(
    db: AsyncSession, *, current_user_id: int, request_id: int
) -> StoreRequestItem:
    req = await crud_sr.get_by_id(db, request_id)
    if req is None or req.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청을 찾을 수 없습니다.",
        )
    return _serialize_request(req)


async def cancel_my_request(
    db: AsyncSession, *, current_user_id: int, request_id: int
) -> None:
    req = await crud_sr.get_by_id(db, request_id)
    if req is None or req.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청을 찾을 수 없습니다.",
        )
    if req.status != StoreRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리된 요청은 취소할 수 없습니다.",
        )
    await crud_sr.delete(db, req)
    await db.commit()


# ─── 관리자측 ─────────────────────────────────────────────────────────────────

async def list_admin_requests(
    db: AsyncSession,
    *,
    status_filter: StoreRequestStatus,
    page: int,
    size: int,
) -> StoreRequestAdminListResponse:
    rows, total = await crud_sr.list_for_admin(
        db, status_filter=status_filter, page=page, size=size
    )
    items = [
        StoreRequestAdminItem(
            request_id=req.id,
            user_id=req.user_id,
            nickname=nickname,
            type=req.type,
            target_store_id=req.target_store_id,
            payload=req.payload,
            proof_urls=list(req.proof_urls or []),
            message=req.message,
            status=req.status,
            reviewer_id=req.reviewer_id,
            review_note=req.review_note,
            processed_at=req.processed_at,
            created_at=req.created_at,
        )
        for req, nickname in rows
    ]
    return StoreRequestAdminListResponse(
        items=items, total=total, page=page, size=size
    )


async def get_admin_request_detail(
    db: AsyncSession, request_id: int
) -> StoreRequestAdminItem:
    from app.crud import user as crud_user

    req = await crud_sr.get_by_id(db, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청을 찾을 수 없습니다.",
        )
    user = await crud_user.get_by_id(db, req.user_id)
    nickname = user.nickname if (user is not None and user.deleted_at is None) else None
    return StoreRequestAdminItem(
        request_id=req.id,
        user_id=req.user_id,
        nickname=nickname,
        type=req.type,
        target_store_id=req.target_store_id,
        payload=req.payload,
        proof_urls=list(req.proof_urls or []),
        message=req.message,
        status=req.status,
        reviewer_id=req.reviewer_id,
        review_note=req.review_note,
        processed_at=req.processed_at,
        created_at=req.created_at,
    )


async def process_admin_request(
    db: AsyncSession,
    *,
    admin_user_id: int,
    request_id: int,
    action: Literal["APPROVE", "REJECT"],
    note: str | None,
) -> StoreRequestProcessedResponse:
    req = await crud_sr.get_by_id(db, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청을 찾을 수 없습니다.",
        )
    if req.status != StoreRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리된 요청입니다.",
        )

    if action == "REJECT":
        await crud_sr.update_status(
            db,
            req,
            new_status=StoreRequestStatus.REJECTED,
            reviewer_id=admin_user_id,
            note=note,
        )
        await _notify_requester(
            db,
            user_id=req.user_id,
            type_=req.type,
            approved=False,
            note=note,
        )
        await db.commit()
        await db.refresh(req)
        return StoreRequestProcessedResponse.model_validate(req)

    # APPROVE
    payload = req.payload or {}
    if req.type == StoreRequestType.ADD:
        await _approve_add(db, req, payload)
    else:
        await _approve_update(db, req, payload)

    await crud_sr.update_status(
        db,
        req,
        new_status=StoreRequestStatus.APPROVED,
        reviewer_id=admin_user_id,
        note=note,
    )
    await _notify_requester(
        db,
        user_id=req.user_id,
        type_=req.type,
        approved=True,
        note=note,
    )
    await db.commit()
    await db.refresh(req)
    return StoreRequestProcessedResponse.model_validate(req)


async def _approve_add(
    db: AsyncSession, req: StoreRequest, payload: dict
) -> Store:
    store = await crud_store.insert_store_from_payload(
        db, payload=payload, owner_user_id=req.user_id
    )
    plans = payload.get("plans") or []
    if plans:
        if store.category != StoreCategory.PET_HOTEL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="가격 플랜은 PET_HOTEL 매장에서만 사용할 수 있습니다.",
            )
        await crud_store.replace_plans(db, store.id, plans)
    return store


async def _approve_update(
    db: AsyncSession, req: StoreRequest, payload: dict
) -> Store:
    store = await crud_store.get_by_id_for_owner(db, req.target_store_id)
    if store is None or store.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상 매장이 사라졌거나 삭제되었습니다.",
        )
    await crud_store.apply_update_payload(db, store, payload)

    if "plans" in payload and payload["plans"] is not None:
        # 카테고리가 PET_HOTEL이 아니면 차단.
        if store.category != StoreCategory.PET_HOTEL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="가격 플랜은 PET_HOTEL 매장에서만 사용할 수 있습니다.",
            )
        await crud_store.replace_plans(db, store.id, payload["plans"])
    elif (
        "category" in payload
        and payload["category"] is not None
        and store.category != StoreCategory.PET_HOTEL
    ):
        # PET_HOTEL → 다른 카테고리로 바뀐 경우 기존 plans 일괄 삭제
        await crud_store.replace_plans(db, store.id, [])
    return store


async def _notify_requester(
    db: AsyncSession,
    *,
    user_id: int,
    type_: StoreRequestType,
    approved: bool,
    note: str | None,
) -> None:
    verb = "추가" if type_ == StoreRequestType.ADD else "수정"
    if approved:
        title = f"매장 {verb} 요청이 승인되었습니다"
        body = "지도에 반영되었습니다." if type_ == StoreRequestType.ADD else "변경 사항이 적용되었습니다."
    else:
        title = f"매장 {verb} 요청이 반려되었습니다"
        body = note or "관리자가 요청을 반려했습니다."
    await notification_service.enqueue(
        db,
        user_id=user_id,
        category=NotificationCategory.SYSTEM,
        title=title,
        body=body,
    )
