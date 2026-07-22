import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MessageAuthorType, MessageType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.support_request import SupportRequest
    from app.models.user import User


class RequestMessage(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "request_messages"

    __table_args__ = (
        CheckConstraint(
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
    )

    support_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "support_requests.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    author_type: Mapped[MessageAuthorType] = mapped_column(
        Enum(
            MessageAuthorType,
            name="message_author_type",
        ),
        nullable=False,
    )

    message_type: Mapped[MessageType] = mapped_column(
        Enum(
            MessageType,
            name="message_type",
        ),
        nullable=False,
        default=MessageType.PUBLIC_REPLY,
        server_default=MessageType.PUBLIC_REPLY.value,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    author_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "contacts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    support_request: Mapped["SupportRequest"] = relationship(
        back_populates="messages",
    )

    author_user: Mapped["User | None"] = relationship(
        back_populates="authored_messages",
    )

    author_contact: Mapped["Contact | None"] = relationship(
        back_populates="authored_messages",
    )
