"""refine support requests for conversations

This migration removes legacy intake fields from support_requests and
introduces a per-organization request number sequence. Downgrade restores
schema shape only; previously dropped channel/external_reference values
cannot be recovered.

Revision ID: c2f8e4b1a9d3
Revises: b8d7c2f41a0e
Create Date: 2026-08-07 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2f8e4b1a9d3"
down_revision: Union[str, Sequence[str], None] = "b8d7c2f41a0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SUPPORT_REQUEST_CHANNEL_ENUM = sa.Enum(
    "WEB_FORM",
    "API",
    "MANUAL",
    name="support_request_channel",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "support_request_sequences",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "last_value",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_value >= 0",
            name="ck_support_request_sequences_last_value_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    op.drop_column("support_requests", "external_reference")
    op.drop_column("support_requests", "channel")

    op.create_index(
        "ix_support_requests_organization_id_created_at",
        "support_requests",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_support_requests_organization_id_status",
        "support_requests",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_support_requests_organization_id_priority",
        "support_requests",
        ["organization_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_support_requests_organization_id_assigned_user_id",
        "support_requests",
        ["organization_id", "assigned_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_support_requests_organization_id_contact_id",
        "support_requests",
        ["organization_id", "contact_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_support_requests_organization_id_contact_id",
        table_name="support_requests",
    )
    op.drop_index(
        "ix_support_requests_organization_id_assigned_user_id",
        table_name="support_requests",
    )
    op.drop_index(
        "ix_support_requests_organization_id_priority",
        table_name="support_requests",
    )
    op.drop_index(
        "ix_support_requests_organization_id_status",
        table_name="support_requests",
    )
    op.drop_index(
        "ix_support_requests_organization_id_created_at",
        table_name="support_requests",
    )

    SUPPORT_REQUEST_CHANNEL_ENUM.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "support_requests",
        sa.Column(
            "channel",
            SUPPORT_REQUEST_CHANNEL_ENUM,
            server_default="MANUAL",
            nullable=False,
        ),
    )
    op.add_column(
        "support_requests",
        sa.Column(
            "external_reference",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.drop_table("support_request_sequences")
