"""update token transaction types

Revision ID: c6cfb11aa2bc
Revises: e5cd7556dfe4
Create Date: 2026-08-09 17:35:52.481859
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c6cfb11aa2bc"
down_revision: Union[str, None] = "e5cd7556dfe4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE tokentransactiontype "
        "ADD VALUE IF NOT EXISTS 'RESERVATION'"
    )

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