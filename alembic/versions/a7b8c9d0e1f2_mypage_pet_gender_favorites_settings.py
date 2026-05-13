"""mypage: pets.gender, store_favorites, notification_settings

Revision ID: a7b8c9d0e1f2
Revises: f3a1c2d4b5e6
Create Date: 2026-05-13 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f3a1c2d4b5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pets.gender ─────────────────────────────────────────────────────────
    pet_gender_enum = sa.Enum("MALE", "FEMALE", "UNKNOWN", name="pet_gender")
    pet_gender_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "pets",
        sa.Column(
            "gender",
            pet_gender_enum,
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
        ),
    )

    # ── store_favorites ─────────────────────────────────────────────────────
    op.create_table(
        "store_favorites",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", name="uq_store_favorites_pair"),
    )
    op.create_index(
        "idx_store_favorites_user_created",
        "store_favorites",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )

    # ── notification_settings ───────────────────────────────────────────────
    # 행이 없으면 push_enabled=TRUE 로 간주(서비스 레이어에서 기본값 처리).
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "VOLUNTEER",
                "MATCH",
                "REVIEW",
                "NEWS",
                "POLICY",
                "SYSTEM",
                name="notification_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "push_enabled",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "category", name="pk_notification_settings"),
    )


def downgrade() -> None:
    op.drop_table("notification_settings")

    op.drop_index("idx_store_favorites_user_created", table_name="store_favorites")
    op.drop_table("store_favorites")

    op.drop_column("pets", "gender")
    sa.Enum(name="pet_gender").drop(op.get_bind(), checkfirst=True)
