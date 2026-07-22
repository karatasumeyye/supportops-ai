import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.request_message import RequestMessage
    from app.models.support_request import SupportRequest



class User( UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    __table_args__ = (
        # cannot have two users with the same normalized email in the same organization
        UniqueConstraint(
            "organization_id",
            "normalized_email",
            name="uq_users_organization_normalized_email",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),  # Restrict deletion of organization if users exist
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
        ),
        nullable=False,
        default=UserRole.SUPPORT_AGENT,
        server_default=UserRole.SUPPORT_AGENT.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships = connect to python classes, not database tables. Use the class name as a string to avoid circular imports.
    organization: Mapped["Organization"] = relationship(
        back_populates="users",   # This should match the attribute name in the Organization class that refers back to User
    )

    assigned_support_requests: Mapped[list["SupportRequest"]] = relationship(
        back_populates="assigned_user",
    )

    authored_messages: Mapped[list["RequestMessage"]] = relationship(
        back_populates="author_user",
    )
