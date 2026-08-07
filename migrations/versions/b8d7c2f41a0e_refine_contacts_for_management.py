"""refine contacts for management

Revision ID: b8d7c2f41a0e
Revises: a1f7f0f2d3b4
Create Date: 2026-08-06 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8d7c2f41a0e"
down_revision: Union[str, Sequence[str], None] = "a1f7f0f2d3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "contacts",
        "email",
        existing_type=sa.String(length=150),
        type_=sa.String(length=320),
        nullable=True,
    )
    op.alter_column(
        "contacts",
        "normalized_email",
        existing_type=sa.String(length=150),
        type_=sa.String(length=320),
        nullable=True,
    )
    op.alter_column(
        "contacts",
        "phone",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
    op.create_index(
        "ix_contacts_organization_id_is_active",
        "contacts",
        ["organization_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    contacts = sa.table(
        "contacts",
        sa.column("id", sa.UUID()),
        sa.column("email", sa.String()),
        sa.column("normalized_email", sa.String()),
        sa.column("phone", sa.String()),
    )

    null_email_ids = connection.execute(
        sa.select(contacts.c.id).where(contacts.c.email.is_(None))
    ).scalars().all()
    if null_email_ids:
        raise RuntimeError(
            "Cannot downgrade contacts: email contains NULL values that the old "
            "schema does not allow."
        )

    null_normalized_email_ids = connection.execute(
        sa.select(contacts.c.id).where(contacts.c.normalized_email.is_(None))
    ).scalars().all()
    if null_normalized_email_ids:
        raise RuntimeError(
            "Cannot downgrade contacts: normalized_email contains NULL values "
            "that the old schema does not allow."
        )

    long_email_ids = connection.execute(
        sa.select(contacts.c.id).where(sa.func.length(contacts.c.email) > 150)
    ).scalars().all()
    if long_email_ids:
        raise RuntimeError(
            "Cannot downgrade contacts: email values longer than 150 characters "
            "exist."
        )

    long_normalized_email_ids = connection.execute(
        sa.select(contacts.c.id).where(
            sa.func.length(contacts.c.normalized_email) > 150
        )
    ).scalars().all()
    if long_normalized_email_ids:
        raise RuntimeError(
            "Cannot downgrade contacts: normalized_email values longer than 150 "
            "characters exist."
        )

    long_phone_ids = connection.execute(
        sa.select(contacts.c.id).where(sa.func.length(contacts.c.phone) > 20)
    ).scalars().all()
    if long_phone_ids:
        raise RuntimeError(
            "Cannot downgrade contacts: phone values longer than 20 characters "
            "exist."
        )

    op.drop_index("ix_contacts_organization_id_is_active", table_name="contacts")
    op.alter_column(
        "contacts",
        "phone",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "normalized_email",
        existing_type=sa.String(length=320),
        type_=sa.String(length=150),
        nullable=False,
    )
    op.alter_column(
        "contacts",
        "email",
        existing_type=sa.String(length=320),
        type_=sa.String(length=150),
        nullable=False,
    )
