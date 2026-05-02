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
