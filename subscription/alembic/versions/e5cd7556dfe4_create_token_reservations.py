
"""create token reservations

Revision ID: e5cd7556dfe4
Revises: 97c2660e21a1
Create Date: 2026-08-09 17:11:52.165861
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e5cd7556dfe4"
down_revision: Union[str, None] = "97c2660e21a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type used by token_reservations.status
    token_reservation_status = postgresql.ENUM(
        "PENDING",
        "SETTLED",
        "RELEASED",
        "EXPIRED",
        name="tokenreservationstatus",
    )

    token_reservation_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "token_reservations",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "request_id",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "reserved_tokens",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "actual_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "refunded_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "input_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "output_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "SETTLED",
                "RELEASED",
                "EXPIRED",
                name="tokenreservationstatus",
                create_type=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "model",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "released_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_token_reservations_user_id",
        "token_reservations",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_token_reservations_request_id",
        "token_reservations",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_token_reservations_request_id",
        table_name="token_reservations",
    )

    op.drop_index(
        "ix_token_reservations_user_id",
        table_name="token_reservations",
    )

    op.drop_table("token_reservations")

    token_reservation_status = postgresql.ENUM(
        "PENDING",
        "SETTLED",
        "RELEASED",
        "EXPIRED",
        name="tokenreservationstatus",
    )

    token_reservation_status.drop(
        op.get_bind(),
        checkfirst=True,
    )

