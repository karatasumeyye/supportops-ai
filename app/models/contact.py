import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.request_message import RequestMessage
    from app.models.support_request import SupportRequest
    from app.models.support_request_access_token import SupportRequestAccessToken


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contacts"

    __table_args__ = (
        # cannot have two contacts with the same email in the same organization
        UniqueConstraint(
            "organization_id",
            "normalized_email",
            name="uq_contacts_organization_normalized_email",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),  # Restrict deletion of organization if contacts exist
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    normalized_email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone: Mapped[str|None] = mapped_column(  #  write None  if nullable =True  
        String(20),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    # Relationship to Organization
    organization: Mapped["Organization"] = relationship(
        back_populates="contacts",
    )

    # Relationship to SupportRequest
    support_requests: Mapped[list["SupportRequest"]] = relationship(
        back_populates="contact",
    )

    authored_messages: Mapped[list["RequestMessage"]] = relationship(
        back_populates="author_contact",
    )

    support_request_access_tokens: Mapped[list["SupportRequestAccessToken"]] = relationship(
        back_populates="contact",
)