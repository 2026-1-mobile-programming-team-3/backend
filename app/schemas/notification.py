from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import NotificationCategory


# ─── 2.1 GET /notifications ──────────────────────────────────────────────────


class NotificationItem(BaseModel):
    id: int
    category: NotificationCategory
    title: str
    body: str
    is_read: bool
    link: str | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    unread_count: int
    page: int
    size: int


# ─── 2.3 GET /notifications/unread-count ─────────────────────────────────────


class UnreadCountResponse(BaseModel):
    unread_count: int


# ─── 2.4 POST /notifications/devices ─────────────────────────────────────────


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(min_length=1)
    device_name: str | None = Field(default=None, max_length=100)


class DeviceRegisteredResponse(BaseModel):
    id: int
    registered_at: datetime


# ─── 2.2 PATCH /notifications/read-all ───────────────────────────────────────


class MarkAllReadResponse(BaseModel):
    updated_count: int
    message: str


# ─── 마이페이지: 카테고리별 push 알림 설정 ────────────────────────────────────


class NotificationSettingsResponse(BaseModel):
    """행이 없는 카테고리는 기본 ON(true)으로 반환."""

    settings: dict[NotificationCategory, bool]


class NotificationSettingsUpdateRequest(BaseModel):
    settings: dict[NotificationCategory, bool] = Field(
        ...,
        description="upsert. 포함된 카테고리만 갱신. 일부만 보내도 됨.",
    )
