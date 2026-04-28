from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import VolunteerRequestStatus


class VolunteerRequest(Base):
    __tablename__ = "volunteer_requests"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[VolunteerRequestStatus] = mapped_column(
        sa.Enum(VolunteerRequestStatus, name="volunteer_request_status"),
        nullable=False,
        default=VolunteerRequestStatus.PENDING,
        server_default=sa.text("'PENDING'"),
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    __table_args__ = (
        # PENDING 중복 신청 금지
        sa.Index(
            "uniq_volunteer_requests_one_pending",
            "user_id",
            unique=True,
            postgresql_where=sa.text("status = 'PENDING'"),
        ),
        sa.Index(
            "idx_volunteer_requests_status_created",
            "status",
            sa.text("created_at DESC"),
        ),
    )
