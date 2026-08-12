import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    ConflictError,
    UnprocessableEntityError,
)
from app.models.contact import Contact
from app.models.enums import (
    MessageAuthorType,
    MessageType,
    SupportRequestPriority,
    SupportRequestStatus,
    UserRole,
)
from app.models.organization import Organization
from app.models.request_message import RequestMessage
from app.models.support_request import SupportRequest
from app.models.user import User
from app.schemas.request_message import ContactMessageCreate, UserMessageCreate
from app.services.request_message import RequestMessageService


def build_organization(*, is_active: bool = True) -> Organization:
    now = datetime.now(timezone.utc)
    return Organization(
        id=uuid4(),
        name="SupportOps",
        slug="supportops",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_contact(
    *,
    organization_id: UUID | None = None,
    is_active: bool = True,
) -> Contact:
    now = datetime.now(timezone.utc)
    return Contact(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        full_name="Contact Name",
        email="contact@example.com",
        normalized_email="contact@example.com",
        phone=None,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_user(
    *,
    organization_id: UUID | None = None,
    role: UserRole = UserRole.AGENT,
    is_active: bool = True,
) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        full_name="Agent User",
        email="agent@example.com",
        normalized_email="agent@example.com",
        password_hash="hash",
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_support_request(
    *,
    organization_id: UUID | None = None,
    contact_id: UUID | None = None,
    status: SupportRequestStatus = SupportRequestStatus.NEW,
    resolved_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> SupportRequest:
    now = datetime.now(timezone.utc)
    return SupportRequest(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        contact_id=contact_id or uuid4(),
        assigned_user_id=None,
        request_number="CONV-000001",
        subject="Need help",
        status=status,
        priority=SupportRequestPriority.MEDIUM,
        resolved_at=resolved_at,
        closed_at=closed_at,
        created_at=now,
        updated_at=now,
    )


def build_message(*, support_request_id: UUID | None = None) -> RequestMessage:
    now = datetime.now(timezone.utc)
    return RequestMessage(
        id=uuid4(),
        support_request_id=support_request_id or uuid4(),
        author_type=MessageAuthorType.USER,
        message_type=MessageType.PUBLIC_REPLY,
        content="Message body",
        author_user_id=uuid4(),
        author_contact_id=None,
        created_at=now,
        updated_at=now,
    )


def build_service() -> tuple[
    RequestMessageService,
    AsyncMock,
    Mock,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    session = AsyncMock()
    service = RequestMessageService(session)
    request_message_repository = Mock()
    request_message_repository.create_message = AsyncMock()
    request_message_repository.get_by_id_and_support_request = AsyncMock()
    request_message_repository.list_messages = AsyncMock()
    support_request_repository = Mock()
    support_request_repository.get_by_id_and_organization = AsyncMock()
    organization_repository = Mock()
    organization_repository.get_by_id = AsyncMock()
    contact_repository = Mock()
    contact_repository.get_by_id_and_organization = AsyncMock()
    user_repository = Mock()
    user_repository.get_by_id_and_organization = AsyncMock()
    service.request_message_repository = request_message_repository
    service.support_request_repository = support_request_repository
    service.organization_repository = organization_repository
    service.contact_repository = contact_repository
    service.user_repository = user_repository
    return (
        service,
        session,
        request_message_repository,
        support_request_repository,
        organization_repository,
        contact_repository,
        user_repository,
    )


def make_cursor(payload: dict[str, str]) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )


def test_encode_and_decode_cursor_round_trip() -> None:
    service, _, _, _, _, _, _ = build_service()
    created_at = datetime.now(timezone.utc).replace(microsecond=123456)
    message_id = uuid4()

    cursor = service._encode_cursor(created_at=created_at, message_id=message_id)
    decoded_created_at, decoded_message_id = service._decode_cursor(cursor)

    assert decoded_created_at == created_at
    assert decoded_message_id == message_id


def test_decode_cursor_rejects_extra_fields() -> None:
    service, _, _, _, _, _, _ = build_service()
    cursor = make_cursor(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "id": str(uuid4()),
            "extra": "field",
        }
    )

    with pytest.raises(UnprocessableEntityError, match="Invalid cursor"):
        service._decode_cursor(cursor)


def test_decode_cursor_rejects_naive_datetime() -> None:
    service, _, _, _, _, _, _ = build_service()
    cursor = make_cursor(
        {
            "created_at": "2026-08-12T10:30:15.123456",
            "id": str(uuid4()),
        }
    )

    with pytest.raises(UnprocessableEntityError, match="Invalid cursor"):
        service._decode_cursor(cursor)


def test_decode_cursor_rejects_invalid_uuid() -> None:
    service, _, _, _, _, _, _ = build_service()
    cursor = make_cursor(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "id": "not-a-uuid",
        }
    )

    with pytest.raises(UnprocessableEntityError, match="Invalid cursor"):
        service._decode_cursor(cursor)


async def test_create_message_raises_conflict_for_closed_conversation() -> None:
    (
        service,
        session,
        request_message_repository,
        support_request_repository,
        organization_repository,
        _contact_repository,
        _user_repository,
    ) = build_service()
    organization = build_organization()
    conversation = build_support_request(
        organization_id=organization.id,
        status=SupportRequestStatus.CLOSED,
    )
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = conversation

    with pytest.raises(
        ConflictError,
        match="Closed conversations cannot accept new messages",
    ):
        await service.create_message(
            organization.id,
            conversation.id,
            UserMessageCreate(
                author_type="USER",
                author_user_id=uuid4(),
                body="Need an update",
                message_type=MessageType.PUBLIC_REPLY,
            ),
        )

    request_message_repository.create_message.assert_not_called()
    session.commit.assert_not_awaited()


async def test_validate_contact_author_raises_conflict_for_wrong_contact() -> None:
    service, _, _, _, _, contact_repository, _ = build_service()
    organization_id = uuid4()
    conversation_contact = build_contact(organization_id=organization_id)
    different_contact = build_contact(organization_id=organization_id)
    conversation = build_support_request(
        organization_id=organization_id,
        contact_id=conversation_contact.id,
    )
    contact_repository.get_by_id_and_organization.return_value = different_contact

    with pytest.raises(ConflictError, match="Contact does not belong to conversation"):
        await service._validate_contact_author(
            organization_id,
            conversation,
            different_contact.id,
        )


async def test_create_message_rolls_back_on_repository_failure() -> None:
    (
        service,
        session,
        request_message_repository,
        support_request_repository,
        organization_repository,
        contact_repository,
        _user_repository,
    ) = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id)
    conversation = build_support_request(
        organization_id=organization.id,
        contact_id=contact.id,
        status=SupportRequestStatus.NEW,
    )
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = conversation
    contact_repository.get_by_id_and_organization.return_value = contact
    request_message_repository.create_message.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await service.create_message(
            organization.id,
            conversation.id,
            ContactMessageCreate(
                author_type="CONTACT",
                author_contact_id=contact.id,
                body="Still broken",
                message_type=MessageType.PUBLIC_REPLY,
            ),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_list_messages_builds_next_cursor_from_last_visible_message() -> None:
    (
        service,
        _,
        request_message_repository,
        support_request_repository,
        organization_repository,
        _,
        _,
    ) = build_service()
    organization = build_organization()
    conversation = build_support_request(organization_id=organization.id)
    first = build_message(support_request_id=conversation.id)
    second = build_message(support_request_id=conversation.id)
    third = build_message(support_request_id=conversation.id)
    second.created_at = first.created_at
    third.created_at = first.created_at
    second.id = uuid4()
    third.id = uuid4()
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = conversation
    request_message_repository.list_messages.return_value = [first, second, third]

    response = await service.list_messages(
        organization.id,
        conversation.id,
        limit=2,
    )

    decoded_created_at, decoded_id = service._decode_cursor(response.next_cursor)
    assert response.has_more is True
    assert len(response.items) == 2
    assert decoded_created_at == second.created_at
    assert decoded_id == second.id
