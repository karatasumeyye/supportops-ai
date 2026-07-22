"""create request messages table

Revision ID: 6c95f31f9d0a
Revises: 2564f4e77e2e
Create Date: 2026-07-22 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c95f31f9d0a"
down_revision: Union[str, Sequence[str], None] = "2564f4e77e2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "request_messages",
        sa.Column("support_request_id", sa.UUID(), nullable=False),
        sa.Column(
            "author_type",
            sa.Enum(
                "CONTACT",
                "USER",
                "SYSTEM",
                name="message_author_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "message_type",
            sa.Enum(
                "PUBLIC_REPLY",
                "INTERNAL_NOTE",
                name="message_type",
            ),
            server_default="PUBLIC_REPLY",
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_user_id", sa.UUID(), nullable=True),
        sa.Column("author_contact_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            (
                author_type = 'USER'
                AND author_user_id IS NOT NULL
                AND author_contact_id IS NULL
            )
            OR
            (
                author_type = 'CONTACT'
                AND author_contact_id IS NOT NULL
                AND author_user_id IS NULL
            )
            OR
            (
                author_type = 'SYSTEM'
                AND author_user_id IS NULL
                AND author_contact_id IS NULL
            )
            """,
            name="ck_request_messages_valid_author",
        ),
        sa.ForeignKeyConstraint(
            ["author_contact_id"],
            ["contacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["support_request_id"],
            ["support_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_request_messages_author_contact_id"),
        "request_messages",
        ["author_contact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_request_messages_author_user_id"),
        "request_messages",
        ["author_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_request_messages_support_request_id"),
        "request_messages",
        ["support_request_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_request_messages_support_request_id"),
        table_name="request_messages",
    )
    op.drop_index(
        op.f("ix_request_messages_author_user_id"),
        table_name="request_messages",
    )
    op.drop_index(
        op.f("ix_request_messages_author_contact_id"),
        table_name="request_messages",
    )
    op.drop_table("request_messages")
