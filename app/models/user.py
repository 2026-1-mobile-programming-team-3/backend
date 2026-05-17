from datetime import datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PetGender, PetSpecies, UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    # 닉네임 UNIQUE 는 partial index (uq_users_nickname_active) 로 분리:
    # soft-deleted 사용자의 닉네임이 영구 점유되지 않도록 활성 사용자끼리만 UNIQUE.
    nickname: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(sa.String(20))
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.USER,
        server_default=sa.text("'USER'"),
    )
    profile_image_url: Mapped[Optional[str]] = mapped_column(sa.Text)
    region_si: Mapped[Optional[str]] = mapped_column(sa.String(50))
    region_dong: Mapped[Optional[str]] = mapped_column(sa.String(50))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    pets: Mapped[list["Pet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        sa.Index("idx_users_role_active", "role", postgresql_where=sa.text("deleted_at IS NULL")),
        sa.Index(
            "uq_users_nickname_active",
            "nickname",
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    fcm_token: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    device_name: Mapped[Optional[str]] = mapped_column(sa.String(100))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    user: Mapped["User"] = relationship(back_populates="devices")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="device")

    __table_args__ = (sa.Index("idx_devices_user_id", "user_id"),)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("devices.id", ondelete="SET NULL")
    )
    token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    device: Mapped[Optional["Device"]] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        sa.Index(
            "idx_refresh_tokens_user_active",
            "user_id",
            postgresql_where=sa.text("revoked_at IS NULL"),
        ),
    )


class Pet(Base):
    __tablename__ = "pets"
    # eager_defaults=True: INSERT 시 server_default 컬럼(created_at, updated_at, is_neutered, gender)
    # 을 RETURNING 으로 한 번에 받아온다. crud.pet.create 에서 db.refresh() 가 하던 SELECT
    # 라운드트립 1개를 절약.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    species: Mapped[PetSpecies] = mapped_column(
        sa.Enum(PetSpecies, name="pet_species"), nullable=False
    )
    breed: Mapped[Optional[str]] = mapped_column(sa.String(50))
    age: Mapped[Optional[int]] = mapped_column(sa.SmallInteger)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(sa.Numeric(5, 2))
    is_neutered: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.text("FALSE")
    )
    gender: Mapped[PetGender] = mapped_column(
        sa.Enum(PetGender, name="pet_gender"),
        nullable=False,
        default=PetGender.UNKNOWN,
        server_default=sa.text("'UNKNOWN'"),
    )
    photo_url: Mapped[Optional[str]] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    user: Mapped["User"] = relationship(back_populates="pets")

    __table_args__ = (
        sa.Index("idx_pets_user_id", "user_id"),
        sa.CheckConstraint("age IS NULL OR age >= 0", name="ck_pets_age_non_negative"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_pets_weight_positive"),
    )
