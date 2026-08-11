import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.models.enums import SupportRequestPriority, SupportRequestStatus
from app.models.request_message import MessageAuthorType, MessageType
from app.schemas.base import APIModel


class SupportRequestCreate(APIModel):
    contact_id: uuid.UUID

    subject: str = Field(
        min_length=1,
        max_length=255,
    )

    initial_message: str = Field(
        min_length=1,
        max_length=10_000,
    )

    priority: SupportRequestPriority = SupportRequestPriority.MEDIUM

    assigned_user_id: uuid.UUID | None = None


class SupportRequestUpdate(APIModel):
    subject: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    priority: SupportRequestPriority | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_update_payload(
        cls,
        data: object,
    ) -> object:
        if not isinstance(data, dict):
            return data

        if not data:
            raise ValueError("At least one field must be provided.")

        if "subject" in data and data["subject"] is None:
            raise ValueError("subject cannot be null.")

        if "priority" in data and data["priority"] is None:
            raise ValueError("priority cannot be null.")

        return data


class SupportRequestAssign(APIModel):
    assigned_user_id: uuid.UUID


class SupportRequestCreateMessageResponse(APIModel):
    id: uuid.UUID
    author_type: MessageAuthorType
    message_type: MessageType
    author_contact_id: uuid.UUID | None
    author_user_id: uuid.UUID | None
    content: str
    created_at: datetime


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
    resolved_at: datetime | None
    closed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class SupportRequestCreateResponse(SupportRequestResponse):
    initial_message: SupportRequestCreateMessageResponse


class SupportRequestListResponse(APIModel):
    items: list[SupportRequestResponse]
    total: int
    limit: int
    offset: int
