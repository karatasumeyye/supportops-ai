import uuid
from datetime import datetime

from pydantic import EmailStr, Field, model_validator

from app.schemas.base import APIModel


class ContactBase(APIModel):
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    email: EmailStr | None = None

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

class ContactCreate(ContactBase):
    organization_id: uuid.UUID

    @model_validator(mode="after")
    def validate_contact_method(self) -> "ContactCreate":
        if self.email is None and self.phone is None:
            raise ValueError(
                "Email veya telefon alanlarindan en az biri girilmelidir."
            )

        return self


class ContactUpdate(APIModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    email: EmailStr | None = None

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

    is_active: bool | None = None


class ContactResponse(ContactBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime