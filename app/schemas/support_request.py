import uuid
from datetime import datetime

from pydantic import Field

from app.models.support_request import (
    SupportRequestChannel,
    SupportRequestPriority,
    SupportRequestStatus,
)
from app.schemas.base import APIModel


class SupportRequestCreate(APIModel):
    contact_id: uuid.UUID

    subject: str = Field(
        min_length=3,
        max_length=200,
    )

    initial_message: str = Field(
        min_length=1,
        max_length=10_000,
    )

    priority: SupportRequestPriority = SupportRequestPriority.MEDIUM

    channel: SupportRequestChannel = SupportRequestChannel.MANUAL

    assigned_user_id: uuid.UUID | None = None

    external_reference: str | None = Field(
        default=None,
        max_length=255,
    )


class SupportRequestUpdate(APIModel):
    subject: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    priority: SupportRequestPriority | None = None

    assigned_user_id: uuid.UUID | None = None

    external_reference: str | None = Field(
        default=None,
        max_length=255,
    )


class SupportRequestStatusUpdate(APIModel):
    status: SupportRequestStatus


class SupportRequestResponse(APIModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    contact_id: uuid.UUID
    assigned_user_id: uuid.UUID | None

    request_number: str
    subject: str

    status: SupportRequestStatus
    priority: SupportRequestPriority
    channel: SupportRequestChannel

    external_reference: str | None
    resolved_at: datetime | None
    closed_at: datetime | None

    created_at: datetime
    updated_at: datetime