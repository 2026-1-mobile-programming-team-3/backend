"""nickname unique → partial unique (active users only)

Revision ID: c5d8f9a0b1e2
Revises: b2c3d4e5f6a7
Create Date: 2026-05-17 13:00:00.000000

기존 users.nickname 은 글로벌 UNIQUE 제약이라 soft-delete 된 사용자의 닉네임이
영구 점유되는 문제가 있었다. 활성 사용자(`deleted_at IS NULL`) 끼리만 UNIQUE
이도록 partial index 로 교체한다.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c5d8f9a0b1e2"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("users_nickname_key", "users", type_="unique")
    op.create_index(
        "uq_users_nickname_active",
        "users",
        ["nickname"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_users_nickname_active", table_name="users")
    op.create_unique_constraint("users_nickname_key", "users", ["nickname"])
