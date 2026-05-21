from datetime import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import StoreRequestStatus, StoreRequestType


class StoreRequest(Base):
    """매장 추가/수정 요청. volunteer_requests와 동일한 검수 패턴.

    승인은 트랜잭션 안에서 stores 테이블 INSERT/UPDATE + pricing plans 처리까지 수행.
    """

    __tablename__ = "store_requests"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[StoreRequestType] = mapped_column(
        sa.Enum(StoreRequestType, name="store_request_type"), nullable=False
    )
    target_store_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("stores.id", ondelete="CASCADE")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    proof_urls: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text),
        nullable=False,
        default=list,
        server_default=sa.text("'{}'::text[]"),
    )
    message: Mapped[Optional[str]] = mapped_column(sa.Text)
    status: Mapped[StoreRequestStatus] = mapped_column(
        sa.Enum(StoreRequestStatus, name="store_request_status"),
        nullable=False,
        default=StoreRequestStatus.PENDING,
        server_default=sa.text("'PENDING'"),
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    review_note: Mapped[Optional[str]] = mapped_column(sa.Text)
    processed_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    __table_args__ = (
        sa.CheckConstraint(
            "(type = 'UPDATE' AND target_store_id IS NOT NULL) "
            "OR (type = 'ADD' AND target_store_id IS NULL)",
            name="ck_store_requests_target_consistency",
        ),
        sa.Index(
            "uniq_store_requests_one_pending_add_per_user",
            "user_id",
            unique=True,
            postgresql_where=sa.text("type = 'ADD' AND status = 'PENDING'"),
        ),
        sa.Index(
            "uniq_store_requests_one_pending_update_per_store",
            "target_store_id",
            unique=True,
            postgresql_where=sa.text("type = 'UPDATE' AND status = 'PENDING'"),
        ),
        sa.Index(
            "idx_store_requests_status_created",
            "status",
            sa.text("created_at DESC"),
        ),
    )
