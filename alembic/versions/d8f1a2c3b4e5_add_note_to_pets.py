"""add note column to pets

Revision ID: d8f1a2c3b4e5
Revises: c5d8f9a0b1e2
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d8f1a2c3b4e5"
down_revision: Union[str, None] = "c5d8f9a0b1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pets", sa.Column("note", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("pets", "note")
