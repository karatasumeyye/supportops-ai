from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING


from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.contact import Contact
    from app.models.support_request import SupportRequest
    from app.models.support_request_access_token import SupportRequestAccessToken

class Organization(
    UUIDPrimaryKeyMixin, TimestampMixin, Base
):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    # list because one organization can have many users (One To Many relationship)
    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
    )

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="organization",
    )

    support_requests: Mapped[list["SupportRequest"]] = relationship(
        back_populates="organization",
    )

    support_request_access_tokens: Mapped[list["SupportRequestAccessToken"]] = relationship(
        back_populates="organization",  
    )