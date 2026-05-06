"""add region_si / region_dong columns to users

Revision ID: e2c9a1b73f48
Revises: d1e2f3a4b5c6
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e2c9a1b73f48'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('region_si', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('region_dong', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'region_dong')
    op.drop_column('users', 'region_si')
