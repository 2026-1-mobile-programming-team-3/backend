from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import NotificationCategory


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[NotificationCategory] = mapped_column(
        sa.Enum(NotificationCategory, name="notification_category"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(sa.String(255))
    read_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    __table_args__ = (
        sa.Index("idx_notifications_user_created", "user_id", sa.text("created_at DESC")),
        sa.Index(
            "idx_notifications_user_unread",
            "user_id",
            sa.text("created_at DESC"),
            postgresql_where=sa.text("read_at IS NULL"),
        ),
    )
