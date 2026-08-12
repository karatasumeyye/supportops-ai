import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from app.models.enums import MessageAuthorType, MessageType
from app.schemas.base import APIModel


class MessageBodyCreate(APIModel):
    body: str = Field(
        min_length=1,
        max_length=10_000,
    )


class ContactMessageCreate(MessageBodyCreate):
    author_type: Literal["CONTACT"]
    author_contact_id: uuid.UUID
    author_user_id: None = None
    message_type: Literal[MessageType.PUBLIC_REPLY] = MessageType.PUBLIC_REPLY


class UserMessageCreate(MessageBodyCreate):
    author_type: Literal["USER"]
    author_contact_id: None = None
    author_user_id: uuid.UUID
    message_type: MessageType


RequestMessageCreate = Annotated[
    ContactMessageCreate | UserMessageCreate,
    Field(discriminator="author_type"),
]


class RequestMessageResponse(APIModel):
    id: uuid.UUID
    conversation_id: uuid.UUID

    author_type: MessageAuthorType
    message_type: MessageType

    body: str

    author_user_id: uuid.UUID | None
    author_contact_id: uuid.UUID | None

    created_at: datetime


class RequestMessageListResponse(APIModel):
    items: list[RequestMessageResponse]
    next_cursor: str | None
    has_more: bool
    limit: int
