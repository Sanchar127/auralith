"""add token reservation transaction types

Revision ID: d1afd0f6be98
Revises: c6cfb11aa2bc
Create Date: 2026-08-09 17:48:49.557857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1afd0f6be98'
down_revision: Union[str, None] = 'c6cfb11aa2bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
