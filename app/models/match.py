from datetime import date, datetime
from typing import Any, Optional

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApplicationStatus, MatchStatus


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    author_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("pets.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    address: Mapped[Optional[str]] = mapped_column(sa.String(255))
    desired_date: Mapped[Optional[date]] = mapped_column(sa.Date)
    status: Mapped[MatchStatus] = mapped_column(
        sa.Enum(MatchStatus, name="match_status"),
        nullable=False,
        default=MatchStatus.WAITING,
        server_default=sa.text("'WAITING'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    applications: Mapped[list["MatchApplication"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["MatchReview"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.Index(
            "idx_matches_status_created",
            "status",
            sa.text("created_at DESC"),
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        sa.Index("idx_matches_location_gist", "location", postgresql_using="gist"),
    )


class MatchApplication(Base):
    __tablename__ = "match_applications"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[Optional[str]] = mapped_column(sa.Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        sa.Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.PENDING,
        server_default=sa.text("'PENDING'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    match: Mapped["Match"] = relationship(back_populates="applications")
    chat_room: Mapped[Optional["ChatRoom"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        sa.UniqueConstraint("match_id", "applicant_id"),
        # 한 매칭당 ACCEPTED 신청자는 1명만 허용
        sa.Index(
            "uniq_match_applications_one_accepted",
            "match_id",
            unique=True,
            postgresql_where=sa.text("status = 'ACCEPTED'"),
        ),
        sa.Index("idx_match_applications_match_status", "match_id", "status"),
    )


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("match_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    application: Mapped["MatchApplication"] = relationship(back_populates="chat_room")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    chat_room_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    room: Mapped["ChatRoom"] = relationship(back_populates="messages")

    __table_args__ = (
        sa.Index(
            "idx_chat_messages_room_created",
            "chat_room_id",
            sa.text("created_at DESC"),
        ),
    )


class MatchReview(Base):
    __tablename__ = "match_reviews"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewee_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(sa.Text)
    proof_image_urls: Mapped[Optional[list[str]]] = mapped_column(sa.ARRAY(sa.Text))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )

    match: Mapped["Match"] = relationship(back_populates="reviews")

    __table_args__ = (
        sa.UniqueConstraint("match_id", "reviewer_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_match_reviews_rating"),
        sa.CheckConstraint(
            "reviewer_id IS NULL OR reviewee_id IS NULL OR reviewer_id <> reviewee_id",
            name="ck_match_reviews_different_users",
        ),
        sa.Index("idx_match_reviews_reviewee", "reviewee_id", sa.text("created_at DESC")),
    )
