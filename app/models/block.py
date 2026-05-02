from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    blocker_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    blocked_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )

    __table_args__ = (
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
        sa.CheckConstraint("blocker_id <> blocked_id", name="ck_user_blocks_no_self"),
        sa.Index(
            "idx_user_blocks_blocker",
            "blocker_id",
            sa.text("created_at DESC"),
        ),
    )
