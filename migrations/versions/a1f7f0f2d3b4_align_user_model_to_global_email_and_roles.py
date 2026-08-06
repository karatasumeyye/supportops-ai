"""align user model to global email and roles

Revision ID: a1f7f0f2d3b4
Revises: 32e1c8b7a4dd
Create Date: 2026-08-06 19:10:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f7f0f2d3b4"
down_revision: str | Sequence[str] | None = "32e1c8b7a4dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _raise_if_global_email_duplicates_exist() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT normalized_email
            FROM users
            WHERE normalized_email IS NOT NULL
            GROUP BY normalized_email
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).scalar_one_or_none()

    if duplicate is not None:
        raise RuntimeError(
            "Cannot migrate users to global unique normalized_email because "
            f"duplicate value exists: {duplicate}"
        )


def _raise_if_owner_rows_exist_for_downgrade() -> None:
    connection = op.get_bind()
    owner_exists = connection.execute(
        sa.text(
            """
            SELECT 1
            FROM users
            WHERE role = 'OWNER'
            LIMIT 1
            """
        )
    ).scalar_one_or_none()

    if owner_exists is not None:
        raise RuntimeError(
            "Cannot downgrade user_role enum while OWNER rows exist."
        )


def upgrade() -> None:
    """Upgrade schema."""
    _raise_if_global_email_duplicates_exist()

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        type_=sa.String(length=320),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "normalized_email",
        existing_type=sa.String(length=255),
        type_=sa.String(length=320),
        existing_nullable=False,
    )

    op.drop_constraint(
        "uq_users_organization_normalized_email",
        "users",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_users_normalized_email",
        "users",
        ["normalized_email"],
    )

    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('OWNER', 'ADMIN', 'AGENT')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE user_role
        USING (
            CASE role::text
                WHEN 'SUPPORT_AGENT' THEN 'AGENT'
                WHEN 'ADMIN' THEN 'ADMIN'
                ELSE role::text
            END
        )::user_role
        """
    )
    op.execute("DROP TYPE user_role_old")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'AGENT'")


def downgrade() -> None:
    """Downgrade schema."""
    _raise_if_owner_rows_exist_for_downgrade()

    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    op.execute("CREATE TYPE user_role AS ENUM ('ADMIN', 'SUPPORT_AGENT')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE user_role
        USING (
            CASE role::text
                WHEN 'AGENT' THEN 'SUPPORT_AGENT'
                WHEN 'ADMIN' THEN 'ADMIN'
                ELSE role::text
            END
        )::user_role
        """
    )
    op.execute("DROP TYPE user_role_new")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'SUPPORT_AGENT'"
    )

    op.drop_constraint(
        "uq_users_normalized_email",
        "users",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_users_organization_normalized_email",
        "users",
        ["organization_id", "normalized_email"],
    )

    op.alter_column(
        "users",
        "normalized_email",
        existing_type=sa.String(length=320),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=320),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
