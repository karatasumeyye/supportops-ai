import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class SupportRequestSequence(Base):
    __tablename__ = "support_request_sequences"

    __table_args__ = (
        CheckConstraint(
            "last_value >= 0",
            name="ck_support_request_sequences_last_value_non_negative",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    last_value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="support_request_sequence",
    )
