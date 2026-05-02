"""add user_blocks table

Revision ID: d1e2f3a4b5c6
Revises: c1a2b3d4e5f6
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_blocks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('blocker_id', sa.BigInteger(), nullable=False),
        sa.Column('blocked_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_blocks_pair'),
        sa.CheckConstraint('blocker_id <> blocked_id', name='ck_user_blocks_no_self'),
    )
    op.create_index(
        'idx_user_blocks_blocker',
        'user_blocks',
        ['blocker_id', sa.text('created_at DESC')],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_user_blocks_blocker', table_name='user_blocks')
    op.drop_table('user_blocks')
