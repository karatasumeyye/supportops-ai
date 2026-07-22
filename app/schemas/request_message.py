import uuid
from datetime import datetime

from pydantic import Field

from app.models.request_message import (
    MessageAuthorType,
    MessageType,
)
from app.schemas.base import APIModel


class MessageContentCreate(APIModel):
    content: str = Field(
        min_length=1,
        max_length=10_000,
    )


class CustomerMessageCreate(MessageContentCreate):
    pass


class AgentReplyCreate(MessageContentCreate):
    pass


class InternalNoteCreate(MessageContentCreate):
    pass


class RequestMessageResponse(APIModel):
    id: uuid.UUID
    support_request_id: uuid.UUID

    author_type: MessageAuthorType
    message_type: MessageType

    content: str

    author_user_id: uuid.UUID | None
    author_contact_id: uuid.UUID | None

    created_at: datetime
    updated_at: datetime