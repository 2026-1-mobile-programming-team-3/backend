"""store requests, pet hotel category, store pricing plans, stores.owner_user_id

Revision ID: e9d4a7c1b2f3
Revises: d8f1a2c3b4e5
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e9d4a7c1b2f3"
down_revision: Union[str, None] = "d8f1a2c3b4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) store_category 에 PET_HOTEL 값 추가.
    # ALTER TYPE ... ADD VALUE 는 Postgres 12+ 부터 트랜잭션 내부에서 허용된다.
    op.execute("ALTER TYPE store_category ADD VALUE IF NOT EXISTS 'PET_HOTEL'")

    # 2) store_requests 용 enum 두 개.
    op.execute("CREATE TYPE store_request_type AS ENUM ('ADD', 'UPDATE')")
    op.execute(
        "CREATE TYPE store_request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')"
    )

    # 3) stores.owner_user_id (인증된 점주).
    op.add_column(
        "stores",
        sa.Column(
            "owner_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_stores_owner_user_id",
        "stores",
        ["owner_user_id"],
        postgresql_where=sa.text("owner_user_id IS NOT NULL"),
    )

    # 4) store_requests 테이블.
    op.create_table(
        "store_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "ADD", "UPDATE", name="store_request_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "target_store_id",
            sa.BigInteger(),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "proof_urls",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                name="store_request_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "reviewer_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "(type = 'UPDATE' AND target_store_id IS NOT NULL) "
            "OR (type = 'ADD' AND target_store_id IS NULL)",
            name="ck_store_requests_target_consistency",
        ),
    )
    op.create_index(
        "uniq_store_requests_one_pending_add_per_user",
        "store_requests",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("type = 'ADD' AND status = 'PENDING'"),
    )
    op.create_index(
        "uniq_store_requests_one_pending_update_per_store",
        "store_requests",
        ["target_store_id"],
        unique=True,
        postgresql_where=sa.text("type = 'UPDATE' AND status = 'PENDING'"),
    )
    op.create_index(
        "idx_store_requests_status_created",
        "store_requests",
        ["status", sa.text("created_at DESC")],
    )

    # 5) store_pricing_plans 테이블 (PET_HOTEL 전용 — 검증은 서비스 레이어).
    op.create_table(
        "store_pricing_plans",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "store_id",
            sa.BigInteger(),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_name", sa.String(length=100), nullable=False),
        sa.Column("price_krw", sa.Integer(), nullable=False),
        sa.Column(
            "display_order",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "price_krw >= 0", name="ck_store_pricing_plans_price_nonneg"
        ),
        sa.UniqueConstraint("store_id", "plan_name", name="uq_store_pricing_plans_name"),
    )
    op.create_index(
        "idx_store_pricing_plans_store_order",
        "store_pricing_plans",
        ["store_id", "display_order"],
    )


def downgrade() -> None:
    op.drop_index("idx_store_pricing_plans_store_order", table_name="store_pricing_plans")
    op.drop_table("store_pricing_plans")

    op.drop_index("idx_store_requests_status_created", table_name="store_requests")
    op.drop_index(
        "uniq_store_requests_one_pending_update_per_store",
        table_name="store_requests",
    )
    op.drop_index(
        "uniq_store_requests_one_pending_add_per_user",
        table_name="store_requests",
    )
    op.drop_table("store_requests")

    op.execute("DROP TYPE IF EXISTS store_request_status")
    op.execute("DROP TYPE IF EXISTS store_request_type")

    op.drop_index("idx_stores_owner_user_id", table_name="stores")
    op.drop_column("stores", "owner_user_id")

    # PET_HOTEL 값은 enum에서 제거 어려움 (Postgres는 ENUM 값 DROP 미지원).
    # 다운그레이드 후에도 PET_HOTEL 값은 enum 정의에 잔존하며, 서비스 레이어에서
    # 사용 안 함으로 처리됨. 정말 제거하려면 enum 재생성 + 컬럼 재바인딩 필요.
