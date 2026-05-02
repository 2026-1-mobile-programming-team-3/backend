from datetime import datetime

from pydantic import BaseModel, Field


# ─── 4.3 POST /users/me/blocks ───────────────────────────────────────────────


class BlockCreateRequest(BaseModel):
    target_user_id: int = Field(gt=0)


class BlockCreatedResponse(BaseModel):
    block_id: int
    target_user_id: int
    created_at: datetime


# ─── 4.4 GET /users/me/blocks ────────────────────────────────────────────────


class BlockListItem(BaseModel):
    block_id: int
    target_user_id: int
    target_nickname: str | None
    created_at: datetime


class BlockListResponse(BaseModel):
    items: list[BlockListItem]
    total: int
