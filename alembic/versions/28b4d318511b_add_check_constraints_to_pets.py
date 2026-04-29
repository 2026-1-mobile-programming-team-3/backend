"""add check constraints to pets

Revision ID: 28b4d318511b
Revises: b71ae8903b66
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '28b4d318511b'
down_revision: Union[str, None] = 'b71ae8903b66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        'ck_pets_age_non_negative',
        'pets',
        'age IS NULL OR age >= 0',
    )
    op.create_check_constraint(
        'ck_pets_weight_positive',
        'pets',
        'weight_kg IS NULL OR weight_kg > 0',
    )


def downgrade() -> None:
    op.drop_constraint('ck_pets_weight_positive', 'pets', type_='check')
    op.drop_constraint('ck_pets_age_non_negative', 'pets', type_='check')
