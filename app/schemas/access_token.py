import uuid
from datetime import datetime, timezone

from pydantic import Field, field_validator

from app.schemas.base import APIModel


class AccessTokenCreate(APIModel):
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return value

        now = datetime.now(timezone.utc)

        if value <= now:
            raise ValueError(
                "Token expiration time must be in the future."
            )

        return value


class AccessTokenResponse(APIModel):
    id: uuid.UUID
    support_request_id: uuid.UUID
    contact_id: uuid.UUID

    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None

    created_at: datetime
    updated_at: datetime


class AccessTokenCreatedResponse(AccessTokenResponse):
    token: str = Field(
        min_length=1,
    )


class AccessTokenRevokeResponse(APIModel):
    id: uuid.UUID
    revoked_at: datetime