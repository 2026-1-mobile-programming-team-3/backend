from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ApplicationStatus


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatMessageItem(BaseModel):
    id: int
    content: str
    sender_id: int | None
    created_at: datetime


class ChatMessageCreatedResponse(ChatMessageItem):
    pass


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageItem]
    has_more: bool
    opponent_last_read_at: datetime | None


class ChatThreadApplicant(BaseModel):
    id: int
    nickname: str | None


class ChatThreadItem(BaseModel):
    application_id: int
    applicant: ChatThreadApplicant
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int
    application_status: ApplicationStatus


class ChatThreadListResponse(BaseModel):
    items: list[ChatThreadItem]
