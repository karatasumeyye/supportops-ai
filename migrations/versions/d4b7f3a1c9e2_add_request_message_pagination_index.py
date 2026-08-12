"""add request message pagination index

Revision ID: d4b7f3a1c9e2
Revises: c2f8e4b1a9d3
Create Date: 2026-08-11 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4b7f3a1c9e2"
down_revision: Union[str, Sequence[str], None] = "c2f8e4b1a9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_request_messages_support_request_id_created_at_id",
        "request_messages",
        ["support_request_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_request_messages_support_request_id_created_at_id",
        table_name="request_messages",
    )
