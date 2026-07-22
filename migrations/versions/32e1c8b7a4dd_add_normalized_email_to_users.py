"""add normalized email to users

Revision ID: 32e1c8b7a4dd
Revises: 2efb75584c86
Create Date: 2026-07-22 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "32e1c8b7a4dd"
down_revision: Union[str, Sequence[str], None] = "2efb75584c86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("normalized_email", sa.String(length=255), nullable=True),
    )
    op.execute("UPDATE users SET normalized_email = lower(email)")
    op.alter_column("users", "normalized_email", nullable=False)
    op.drop_constraint("uq_users_organization_email", "users", type_="unique")
    op.create_unique_constraint(
        "uq_users_organization_normalized_email",
        "users",
        ["organization_id", "normalized_email"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_users_organization_normalized_email",
        "users",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_users_organization_email",
        "users",
        ["organization_id", "email"],
    )
    op.drop_column("users", "normalized_email")
