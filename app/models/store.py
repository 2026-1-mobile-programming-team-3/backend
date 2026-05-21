from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StoreCategory, StoreStatus


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    address: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(sa.String(20))
    category: Mapped[StoreCategory] = mapped_column(
        sa.Enum(StoreCategory, name="store_category"), nullable=False
    )
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    operating_hours: Mapped[Optional[str]] = mapped_column(sa.String(100))
    photo_urls: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text), nullable=False, default=list, server_default=sa.text("'{}'::text[]")
    )
    is_pet_allowed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.text("TRUE")
    )
    status: Mapped[StoreStatus] = mapped_column(
        sa.Enum(StoreStatus, name="store_status"),
        nullable=False,
        default=StoreStatus.PENDING,
        server_default=sa.text("'PENDING'"),
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    rating_avg: Mapped[Decimal] = mapped_column(
        sa.Numeric(3, 2), nullable=False, default=0, server_default=sa.text("0")
    )
    rating_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    reviews: Mapped[list["StoreReview"]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )
    pricing_plans: Mapped[list["StorePricingPlan"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
        order_by="StorePricingPlan.display_order",
    )

    __table_args__ = (
        sa.Index("idx_stores_location_gist", "location", postgresql_using="gist"),
        sa.Index(
            "idx_stores_status_category",
            "status",
            "category",
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
    )


class StoreReview(Base):
    __tablename__ = "store_reviews"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    is_pet_allowed: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    store: Mapped["Store"] = relationship(back_populates="reviews")

    __table_args__ = (
        sa.UniqueConstraint("store_id", "author_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_store_reviews_rating"),
        sa.Index("idx_store_reviews_store_created", "store_id", sa.text("created_at DESC")),
    )


class StorePricingPlan(Base):
    """PET_HOTEL 매장의 가격 플랜. 1매장 N플랜.
    카테고리 != PET_HOTEL 인 매장에 plan 추가는 서비스 레이어에서 차단."""

    __tablename__ = "store_pricing_plans"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    price_krw: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(
        sa.SmallInteger, nullable=False, default=0, server_default=sa.text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    store: Mapped["Store"] = relationship(back_populates="pricing_plans")

    __table_args__ = (
        sa.CheckConstraint("price_krw >= 0", name="ck_store_pricing_plans_price_nonneg"),
        sa.UniqueConstraint("store_id", "plan_name", name="uq_store_pricing_plans_name"),
        sa.Index("idx_store_pricing_plans_store_order", "store_id", "display_order"),
    )
