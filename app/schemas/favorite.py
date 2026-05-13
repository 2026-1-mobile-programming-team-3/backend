from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.enums import StoreCategory


class FavoriteCreateRequest(BaseModel):
    store_id: int


class FavoriteCreatedResponse(BaseModel):
    favorite_id: int
    store_id: int
    created_at: datetime


class FavoriteListItem(BaseModel):
    favorite_id: int
    store_id: int
    name: str
    category: StoreCategory
    thumbnail_url: Optional[str]
    rating_avg: Decimal
    created_at: datetime


class FavoriteListResponse(BaseModel):
    items: list[FavoriteListItem]
    total: int
    page: int
    size: int
