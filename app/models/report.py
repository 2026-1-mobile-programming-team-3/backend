from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ReportType


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_user_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    report_type: Mapped[ReportType] = mapped_column(
        sa.Enum(ReportType, name="report_type"),
        nullable=False,
        default=ReportType.USER,
        server_default=sa.text("'USER'"),
    )
    chat_room_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("chat_rooms.id", ondelete="SET NULL")
    )
    message_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    __table_args__ = (
        # USER 신고는 신고자-피신고자 쌍이 유일. CHAT 신고는 메시지 단위라 자유.
        sa.Index(
            "ux_reports_user_pair",
            "reporter_id",
            "target_user_id",
            unique=True,
            postgresql_where=sa.text("report_type = 'USER'"),
        ),
        sa.Index("idx_reports_target_created", "target_user_id", sa.text("created_at DESC")),
        sa.CheckConstraint(
            "report_type = 'USER' OR (chat_room_id IS NOT NULL AND message_id IS NOT NULL)",
            name="ck_reports_chat_refs",
        ),
    )
