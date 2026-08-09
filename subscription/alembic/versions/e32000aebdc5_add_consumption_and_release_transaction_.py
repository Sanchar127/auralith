"""add consumption and release transaction types

Revision ID: e32000aebdc5
Revises: d1afd0f6be98
Create Date: 2026-08-09 17:50:23.418267
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e32000aebdc5"
down_revision: Union[str, None] = "d1afd0f6be98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE tokentransactiontype "
        "ADD VALUE IF NOT EXISTS 'CONSUMPTION'"
    )

    op.execute(
        "ALTER TYPE tokentransactiontype "
        "ADD VALUE IF NOT EXISTS 'RELEASE'"
    )


def downgrade() -> None:
    # PostgreSQL does not support directly removing enum values.
    pass