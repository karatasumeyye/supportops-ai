import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    SupportRequestPriority,
    SupportRequestStatus,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.organization import Organization
    from app.models.request_message import RequestMessage
    from app.models.support_request_access_token import SupportRequestAccessToken
    from app.models.user import User


class SupportRequest(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "support_requests"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "request_number",
            name="uq_support_requests_organization_request_number",
        ),
        Index(
            "ix_support_requests_organization_id_created_at",
            "organization_id",
            "created_at",
        ),
        Index(
            "ix_support_requests_organization_id_status",
            "organization_id",
            "status",
        ),
        Index(
            "ix_support_requests_organization_id_priority",
            "organization_id",
            "priority",
        ),
        Index(
            "ix_support_requests_organization_id_assigned_user_id",
            "organization_id",
            "assigned_user_id",
        ),
        Index(
            "ix_support_requests_organization_id_contact_id",
            "organization_id",
            "contact_id",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "contacts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    request_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[SupportRequestStatus] = mapped_column(
        Enum(
            SupportRequestStatus,
            name="support_request_status",
        ),
        nullable=False,
        default=SupportRequestStatus.NEW,
        server_default=SupportRequestStatus.NEW.value,
        index=True,
    )

    priority: Mapped[SupportRequestPriority] = mapped_column(
        Enum(
            SupportRequestPriority,
            name="support_request_priority",
        ),
        nullable=False,
        default=SupportRequestPriority.MEDIUM,
        server_default=SupportRequestPriority.MEDIUM.value,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="support_requests",
    )

    contact: Mapped["Contact"] = relationship(
        back_populates="support_requests",
    )

    assigned_user: Mapped["User | None"] = relationship(
        back_populates="assigned_support_requests",
    )

    messages: Mapped[list["RequestMessage"]] = relationship(
        back_populates="support_request",
        cascade="all, delete-orphan",
        order_by="RequestMessage.created_at",
    )

    access_tokens: Mapped[list["SupportRequestAccessToken"]] = relationship(
        back_populates="support_request",
        cascade="all, delete-orphan",
    )
