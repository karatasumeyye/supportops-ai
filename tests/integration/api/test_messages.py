import base64
import json
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    MessageAuthorType,
    MessageType,
)
from app.models.request_message import RequestMessage
from app.repositories.request_message import RequestMessageRepository


async def create_organization(
    client: AsyncClient,
    *,
    name: str,
    slug: str,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/organizations",
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 201
    return cast(dict[str, str], response.json())


async def deactivate_organization(
    client: AsyncClient,
    organization_id: str,
) -> None:
    response = await client.patch(
        f"/api/v1/organizations/{organization_id}",
        json={"is_active": False},
    )
    assert response.status_code == 200


async def create_contact(
    client: AsyncClient,
    organization_id: str,
    *,
    full_name: str = "Message Contact",
    email: str | None = "message.contact@example.com",
    phone: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"full_name": full_name}
    if email is not None:
        payload["email"] = email
    if phone is not None:
        payload["phone"] = phone

    response = await client.post(
        f"/api/v1/organizations/{organization_id}/contacts",
        json=payload,
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def deactivate_contact(
    client: AsyncClient,
    organization_id: str,
    contact_id: str,
) -> None:
    response = await client.post(
        f"/api/v1/organizations/{organization_id}/contacts/{contact_id}/deactivate",
    )
    assert response.status_code == 200


async def create_user(
    client: AsyncClient,
    organization_id: str,
    *,
    full_name: str = "Message Agent",
    email: str = "message.agent@example.com",
    role: str = "AGENT",
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/organizations/{organization_id}/users",
        json={
            "full_name": full_name,
            "email": email,
            "password": "strongpass123",
            "role": role,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def deactivate_user(
    client: AsyncClient,
    organization_id: str,
    user_id: str,
) -> None:
    response = await client.patch(
        f"/api/v1/organizations/{organization_id}/users/{user_id}",
        json={"is_active": False},
    )
    assert response.status_code == 200


async def create_conversation(
    client: AsyncClient,
    organization_id: str,
    *,
    contact_id: str,
    subject: str = "Message conversation",
    initial_message: str = "Initial customer message",
    assigned_user_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "contact_id": contact_id,
        "subject": subject,
        "initial_message": initial_message,
    }
    if assigned_user_id is not None:
        payload["assigned_user_id"] = assigned_user_id

    response = await client.post(
        f"/api/v1/organizations/{organization_id}/conversations",
        json=payload,
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def encode_cursor(payload: dict[str, str]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode(
        "utf-8"
    )
    return encoded.rstrip("=")


def decode_cursor(cursor: str) -> dict[str, str]:
    padding = "=" * (-len(cursor) % 4)
    decoded = base64.urlsafe_b64decode(f"{cursor}{padding}")
    return cast(dict[str, str], json.loads(decoded.decode("utf-8")))


def parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def test_contact_public_message_create_and_response_shape(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Message Organization",
        slug="message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "  Sorun hala devam ediyor.  ",
        },
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["conversation_id"] == conversation["id"]
    assert response_data["author_type"] == "CONTACT"
    assert response_data["author_contact_id"] == contact["id"]
    assert response_data["author_user_id"] is None
    assert response_data["message_type"] == "PUBLIC_REPLY"
    assert response_data["body"] == "Sorun hala devam ediyor."
    assert "support_request_id" not in response_data
    assert "updated_at" not in response_data


async def test_user_internal_note_create_succeeds(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Internal Note Organization",
        slug="internal-note-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "USER",
            "author_user_id": user["id"],
            "message_type": "INTERNAL_NOTE",
            "body": "Need escalation.",
        },
    )

    assert response.status_code == 201
    assert response.json()["message_type"] == "INTERNAL_NOTE"


async def test_resolved_conversation_accepts_message_without_status_change(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Resolved Message Organization",
        slug="resolved-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    transition_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "RESOLVED"},
    )
    assert transition_response.status_code == 200

    message_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Issue returned.",
        },
    )
    detail_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
    )

    assert message_response.status_code == 201
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "RESOLVED"


async def test_closed_conversation_blocks_message_create_but_allows_list(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Closed Message Organization",
        slug="closed-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    close_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "CLOSED"},
    )
    assert close_response.status_code == 200

    create_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Still happening",
        },
    )
    list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
    )

    assert create_response.status_code == 409
    assert list_response.status_code == 200


async def test_initial_and_later_messages_list_with_conversation_id(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Message Listing Organization",
        slug="message-listing-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="listing-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        initial_message="Initial timeline message",
    )

    create_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "USER",
            "author_user_id": user["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Follow-up reply",
        },
    )
    assert create_response.status_code == 201

    list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
    )

    assert list_response.status_code == 200
    response_data = list_response.json()
    assert response_data["limit"] == 50
    assert response_data["has_more"] is False
    assert response_data["next_cursor"] is None
    assert len(response_data["items"]) == 2
    assert response_data["items"][0]["conversation_id"] == conversation["id"]
    assert response_data["items"][0]["body"] == "Initial timeline message"
    assert response_data["items"][1]["conversation_id"] == conversation["id"]
    assert response_data["items"][1]["body"] == "Follow-up reply"


async def test_message_pagination_next_cursor_uses_last_returned_message(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Pagination Message Organization",
        slug="pagination-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    for index in range(3):
        response = await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
            json={
                "author_type": "CONTACT",
                "author_contact_id": contact["id"],
                "message_type": "PUBLIC_REPLY",
                "body": f"Message {index}",
            },
        )
        assert response.status_code == 201

    first_page = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages?limit=2",
    )
    assert first_page.status_code == 200
    first_page_data = first_page.json()
    decoded_cursor = decode_cursor(first_page_data["next_cursor"])
    last_visible_message = first_page_data["items"][-1]

    assert first_page_data["has_more"] is True
    assert decoded_cursor["id"] == last_visible_message["id"]
    assert parse_api_datetime(decoded_cursor["created_at"]) == parse_api_datetime(
        last_visible_message["created_at"]
    )

    second_page = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages"
        f"?limit=2&cursor={first_page_data['next_cursor']}"
    )
    assert second_page.status_code == 200
    second_page_data = second_page.json()
    returned_ids = [item["id"] for item in first_page_data["items"]] + [
        item["id"] for item in second_page_data["items"]
    ]

    assert len(returned_ids) == len(set(returned_ids))


async def test_message_validation_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Validation Message Organization",
        slug="validation-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="validation-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    invalid_payloads = [
        {
            "message_type": "PUBLIC_REPLY",
            "body": "Missing author",
        },
        {
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "   ",
        },
        {
            "author_type": "SYSTEM",
            "message_type": "PUBLIC_REPLY",
            "body": "Should fail",
        },
        {
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "INTERNAL_NOTE",
            "body": "Should fail",
        },
        {
            "author_type": "USER",
            "author_user_id": user["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Okay",
            "created_at": "2026-08-12T10:00:00Z",
        },
    ]

    for payload in invalid_payloads:
        response = await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
            json=payload,
        )
        assert response.status_code == 422


async def test_message_cursor_validation_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Cursor Message Organization",
        slug="cursor-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    invalid_cursors = [
        "not-base64",
        encode_cursor(
            {
                "created_at": "2026-08-12T10:30:15.123456+00:00",
                "id": str(uuid4()),
                "extra": "field",
            }
        ),
        encode_cursor(
            {
                "created_at": "2026-08-12T10:30:15.123456",
                "id": str(uuid4()),
            }
        ),
        encode_cursor(
            {
                "created_at": "2026-08-12T10:30:15.123456+00:00",
                "id": "not-a-uuid",
            }
        ),
    ]

    for cursor in invalid_cursors:
        response = await client.get(
            f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages?cursor={cursor}",
        )
        assert response.status_code == 422


async def test_cross_tenant_and_wrong_contact_rules(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Tenant A Message Organization",
        slug="tenant-a-message-organization",
    )
    organization_b = await create_organization(
        client,
        name="Tenant B Message Organization",
        slug="tenant-b-message-organization",
    )
    contact_a = await create_contact(client, organization_a["id"])
    contact_b = await create_contact(
        client,
        organization_b["id"],
        email="tenant-b-contact@example.com",
    )
    same_tenant_wrong_contact = await create_contact(
        client,
        organization_a["id"],
        email="same-tenant-wrong@example.com",
    )
    user_b = await create_user(
        client,
        organization_b["id"],
        email="cross-tenant-message-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization_a["id"],
        contact_id=str(contact_a["id"]),
    )

    cross_tenant_contact_response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact_b["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Wrong tenant",
        },
    )
    wrong_contact_response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": same_tenant_wrong_contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Wrong contact",
        },
    )
    cross_tenant_user_response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "USER",
            "author_user_id": user_b["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Wrong user",
        },
    )
    cross_tenant_list_response = await client.get(
        f"/api/v1/organizations/{organization_b['id']}/conversations/{conversation['id']}/messages",
    )

    assert cross_tenant_contact_response.status_code == 404
    assert wrong_contact_response.status_code == 409
    assert cross_tenant_user_response.status_code == 404
    assert cross_tenant_list_response.status_code == 404


async def test_inactive_resource_rules_for_messages(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Inactive Resource Message Organization",
        slug="inactive-resource-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="inactive-resource-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    await deactivate_contact(client, organization["id"], str(contact["id"]))
    inactive_contact_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Still broken",
        },
    )

    await deactivate_user(client, organization["id"], str(user["id"]))
    inactive_user_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "USER",
            "author_user_id": user["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Checking in",
        },
    )

    list_before_org_deactivate = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
    )
    await deactivate_organization(client, organization["id"])
    inactive_org_create_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "author_type": "CONTACT",
            "author_contact_id": contact["id"],
            "message_type": "PUBLIC_REPLY",
            "body": "Blocked now",
        },
    )
    inactive_org_list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
    )

    assert inactive_contact_response.status_code == 409
    assert inactive_user_response.status_code == 409
    assert list_before_org_deactivate.status_code == 200
    assert inactive_org_create_response.status_code == 409
    assert inactive_org_list_response.status_code == 200


async def test_failed_message_create_does_not_mutate_conversation_state(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = await create_organization(
        client,
        name="Rollback Message Organization",
        slug="rollback-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )
    before_detail = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
    )
    assert before_detail.status_code == 200

    async def broken_create_message(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("message persistence failed")

    monkeypatch.setattr(
        RequestMessageRepository,
        "create_message",
        broken_create_message,
    )

    with pytest.raises(RuntimeError):
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
            json={
                "author_type": "CONTACT",
                "author_contact_id": contact["id"],
                "message_type": "PUBLIC_REPLY",
                "body": "Will fail",
            },
        )

    monkeypatch.undo()
    after_detail = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
    )
    assert after_detail.status_code == 200
    assert after_detail.json()["status"] == before_detail.json()["status"]
    assert after_detail.json()["resolved_at"] == before_detail.json()["resolved_at"]
    assert after_detail.json()["closed_at"] == before_detail.json()["closed_at"]


async def test_request_message_db_constraint_rejects_invalid_author_shapes(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(
        client,
        name="Constraint Message Organization",
        slug="constraint-message-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="constraint-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    invalid_messages = [
        RequestMessage(
            support_request_id=conversation["id"],
            author_type=MessageAuthorType.CONTACT,
            message_type=MessageType.PUBLIC_REPLY,
            content="Invalid contact message",
            author_contact_id=None,
            author_user_id=None,
        ),
        RequestMessage(
            support_request_id=conversation["id"],
            author_type=MessageAuthorType.USER,
            message_type=MessageType.PUBLIC_REPLY,
            content="Invalid user message",
            author_contact_id=contact["id"],
            author_user_id=user["id"],
        ),
    ]

    for invalid_message in invalid_messages:
        db_session.add(invalid_message)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


async def test_request_message_db_constraint_accepts_valid_system_rows(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(
        client,
        name="System Constraint Organization",
        slug="system-constraint-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    system_message = RequestMessage(
        support_request_id=conversation["id"],
        author_type=MessageAuthorType.SYSTEM,
        message_type=MessageType.INTERNAL_NOTE,
        content="System generated note",
        author_contact_id=None,
        author_user_id=None,
    )

    db_session.add(system_message)
    await db_session.commit()
    await db_session.refresh(system_message)

    assert system_message.id is not None
