import re
import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import APIModel


class OrganizationBase(APIModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )


class OrganizationCreate(OrganizationBase):
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Slug yalnizca kucuk harf, sayi ve tek tire gruplari icerebilir."
            )

        return value


class OrganizationUpdate(APIModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Slug yalnizca kucuk harf, sayi ve tek tire gruplari icerebilir."
            )

        return value


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
