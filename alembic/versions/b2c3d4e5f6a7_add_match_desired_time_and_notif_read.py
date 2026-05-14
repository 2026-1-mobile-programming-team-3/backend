"""add matches.desired_time column

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-05-14 10:00:00.000000

매칭 카드/상세에서 "오전 10:00 출발 예정" 같은 시간 표시 지원을 위해
matches.desired_time (TIME) 컬럼을 추가한다. NULL 허용.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("desired_time", sa.Time(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "desired_time")
