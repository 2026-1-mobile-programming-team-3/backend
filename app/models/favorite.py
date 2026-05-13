from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StoreFavorite(Base):
    __tablename__ = "store_favorites"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "store_id", name="uq_store_favorites_pair"),
        sa.Index(
            "idx_store_favorites_user_created",
            "user_id",
            sa.text("created_at DESC"),
        ),
    )
