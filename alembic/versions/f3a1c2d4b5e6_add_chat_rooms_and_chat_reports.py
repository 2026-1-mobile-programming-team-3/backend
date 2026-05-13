"""add chat_rooms, move chat_messages to chat_room_id, extend reports for chat reports

Revision ID: f3a1c2d4b5e6
Revises: e2c9a1b73f48
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a1c2d4b5e6"
down_revision: Union[str, None] = "e2c9a1b73f48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── chat_rooms (신규) ────────────────────────────────────────────────────
    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("application_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["match_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_chat_rooms_application_id"),
    )

    # ── chat_messages: application_id → chat_room_id 이행 ────────────────────
    op.add_column(
        "chat_messages",
        sa.Column("chat_room_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_messages_chat_room_id",
        "chat_messages",
        "chat_rooms",
        ["chat_room_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 백필: 기존 chat_messages.application_id별로 chat_rooms 행 생성 후 chat_room_id 채움
    op.execute(
        """
        INSERT INTO chat_rooms (application_id, created_at)
        SELECT application_id, MIN(created_at)
          FROM chat_messages
         GROUP BY application_id
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE chat_messages cm
           SET chat_room_id = cr.id
          FROM chat_rooms cr
         WHERE cr.application_id = cm.application_id
           AND cm.chat_room_id IS NULL
        """
    )

    op.alter_column("chat_messages", "chat_room_id", nullable=False)
    op.drop_index("idx_chat_messages_application_created", table_name="chat_messages")
    op.drop_constraint(
        "chat_messages_application_id_fkey", "chat_messages", type_="foreignkey"
    )
    op.drop_column("chat_messages", "application_id")
    op.create_index(
        "idx_chat_messages_room_created",
        "chat_messages",
        ["chat_room_id", sa.text("created_at DESC")],
        unique=False,
    )

    # ── reports 확장: 채팅 신고 지원 ─────────────────────────────────────────
    report_type_enum = sa.Enum("USER", "CHAT", name="report_type")
    report_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "reports",
        sa.Column(
            "report_type",
            report_type_enum,
            nullable=False,
            server_default=sa.text("'USER'"),
        ),
    )
    op.add_column(
        "reports",
        sa.Column("chat_room_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_reports_chat_room_id",
        "reports",
        "chat_rooms",
        ["chat_room_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_reports_message_id",
        "reports",
        "chat_messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 기존 UNIQUE(reporter_id, target_user_id) 해제 → USER 신고에만 partial unique 적용
    op.drop_constraint(
        "reports_reporter_id_target_user_id_key", "reports", type_="unique"
    )
    op.create_index(
        "ux_reports_user_pair",
        "reports",
        ["reporter_id", "target_user_id"],
        unique=True,
        postgresql_where=sa.text("report_type = 'USER'"),
    )

    op.create_check_constraint(
        "ck_reports_chat_refs",
        "reports",
        "report_type = 'USER' OR (chat_room_id IS NOT NULL AND message_id IS NOT NULL)",
    )


def downgrade() -> None:
    # reports 원복
    op.drop_constraint("ck_reports_chat_refs", "reports", type_="check")
    op.drop_index("ux_reports_user_pair", table_name="reports")
    op.create_unique_constraint(
        "reports_reporter_id_target_user_id_key",
        "reports",
        ["reporter_id", "target_user_id"],
    )
    op.drop_constraint("fk_reports_message_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_chat_room_id", "reports", type_="foreignkey")
    op.drop_column("reports", "message_id")
    op.drop_column("reports", "chat_room_id")
    op.drop_column("reports", "report_type")
    sa.Enum(name="report_type").drop(op.get_bind(), checkfirst=True)

    # chat_messages 원복
    op.drop_index("idx_chat_messages_room_created", table_name="chat_messages")
    op.add_column(
        "chat_messages",
        sa.Column("application_id", sa.BigInteger(), nullable=True),
    )
    op.execute(
        """
        UPDATE chat_messages cm
           SET application_id = cr.application_id
          FROM chat_rooms cr
         WHERE cr.id = cm.chat_room_id
        """
    )
    op.alter_column("chat_messages", "application_id", nullable=False)
    op.create_foreign_key(
        "chat_messages_application_id_fkey",
        "chat_messages",
        "match_applications",
        ["application_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "idx_chat_messages_application_created",
        "chat_messages",
        ["application_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.drop_constraint(
        "fk_chat_messages_chat_room_id", "chat_messages", type_="foreignkey"
    )
    op.drop_column("chat_messages", "chat_room_id")

    op.drop_table("chat_rooms")
