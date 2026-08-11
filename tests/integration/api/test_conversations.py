import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies.database import get_db_session
from app.main import create_application


async def create_organization(
    client: AsyncClient,
    *,
    name: str,
    slug: str,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/organizations",
        json={
            "name": name,
            "slug": slug,
        },
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
    full_name: str = "Conversation Contact",
    email: str | None = "conversation.contact@example.com",
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
    full_name: str = "Conversation Agent",
    email: str = "conversation.agent@example.com",
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
    subject: str = "Conversation subject",
    initial_message: str = "Initial customer message",
    priority: str = "MEDIUM",
    assigned_user_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "contact_id": contact_id,
        "subject": subject,
        "initial_message": initial_message,
        "priority": priority,
    }
    if assigned_user_id is not None:
        payload["assigned_user_id"] = assigned_user_id

    response = await client.post(
        f"/api/v1/organizations/{organization_id}/conversations",
        json=payload,
    )

    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@asynccontextmanager
async def isolated_client() -> AsyncIterator[AsyncClient]:
    application = create_application()
    isolated_engine = create_async_engine(
        os.environ["TEST_DATABASE_URL"],
        echo=False,
        poolclass=pool.NullPool,
    )
    isolated_session_factory = async_sessionmaker(
        bind=isolated_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with isolated_session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    application.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=application)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    application.dependency_overrides.clear()
    await isolated_engine.dispose()


async def test_create_unassigned_conversation(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Organization",
        slug="conversation-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        email="conversation-contact@example.com",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={
            "contact_id": contact["id"],
            "subject": "Need billing help",
            "initial_message": "I was charged twice.",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["organization_id"] == organization["id"]
    assert response_data["contact_id"] == contact["id"]
    assert response_data["assigned_user_id"] is None
    assert response_data["subject"] == "Need billing help"
    assert response_data["status"] == "NEW"
    assert response_data["priority"] == "MEDIUM"
    assert response_data["request_number"].startswith("CONV-")
    assert response_data["resolved_at"] is None
    assert response_data["closed_at"] is None
    assert response_data["initial_message"]["author_type"] == "CONTACT"
    assert response_data["initial_message"]["message_type"] == "PUBLIC_REPLY"
    assert response_data["initial_message"]["author_contact_id"] == contact["id"]
    assert response_data["initial_message"]["author_user_id"] is None
    assert response_data["initial_message"]["content"] == "I was charged twice."


async def test_create_assigned_conversation(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Assigned Conversation Organization",
        slug="assigned-conversation-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        email="assigned-contact@example.com",
    )
    user = await create_user(
        client,
        organization["id"],
        email="assigned-agent@example.com",
    )

    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        assigned_user_id=str(user["id"]),
    )

    assert conversation["assigned_user_id"] == user["id"]
    assert conversation["priority"] == "MEDIUM"


async def test_get_conversation_detail(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Detail Organization",
        slug="conversation-detail-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        subject="Detail subject",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Detail subject"


async def test_list_conversations_default_pagination(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation List Organization",
        slug="conversation-list-organization",
    )
    contact = await create_contact(client, organization["id"])

    for index in range(25):
        await create_conversation(
            client,
            organization["id"],
            contact_id=str(contact["id"]),
            subject=f"Conversation {index}",
        )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
    )

    assert response.status_code == 200
    assert response.json()["limit"] == 20
    assert response.json()["offset"] == 0
    assert response.json()["total"] == 25
    assert len(response.json()["items"]) == 20


async def test_list_conversations_filters_and_search(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Filter Organization",
        slug="conversation-filter-organization",
    )
    contact = await create_contact(client, organization["id"])
    assigned_user = await create_user(
        client,
        organization["id"],
        email="filter-agent@example.com",
    )

    first = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        subject="Password reset issue",
        assigned_user_id=str(assigned_user["id"]),
    )
    second = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        subject="Payment duplicate",
        priority="URGENT",
    )

    transition_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{first['id']}/transition",
        json={"status": "IN_PROGRESS"},
    )
    assert transition_response.status_code == 200

    status_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?status=IN_PROGRESS",
    )
    priority_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?priority=URGENT",
    )
    assigned_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?assigned_user_id={assigned_user['id']}",
    )
    unassigned_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?unassigned=true",
    )
    search_subject_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?search=password",
    )
    search_number_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?search={second['request_number']}",
    )

    assert status_response.status_code == 200
    assert priority_response.status_code == 200
    assert assigned_response.status_code == 200
    assert unassigned_response.status_code == 200
    assert search_subject_response.status_code == 200
    assert search_number_response.status_code == 200

    assert status_response.json()["items"][0]["id"] == first["id"]
    assert priority_response.json()["items"][0]["id"] == second["id"]
    assert assigned_response.json()["items"][0]["id"] == first["id"]
    assert unassigned_response.json()["items"][0]["id"] == second["id"]
    assert search_subject_response.json()["items"][0]["id"] == first["id"]
    assert search_number_response.json()["items"][0]["id"] == second["id"]


async def test_whitespace_search_is_ignored(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Whitespace Search Organization",
        slug="whitespace-search-organization",
    )
    contact = await create_contact(client, organization["id"])
    await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        subject="Only conversation",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations?search=%20%20%20",
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_update_conversation_subject_and_priority(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Update Organization",
        slug="conversation-update-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        json={
            "subject": "Updated subject",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Updated subject"
    assert response.json()["priority"] == "HIGH"


async def test_assign_same_user_is_idempotent(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Assign Idempotent Organization",
        slug="assign-idempotent-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="assign-idempotent-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
        assigned_user_id=str(user["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/assign",
        json={"assigned_user_id": user["id"]},
    )

    assert response.status_code == 200
    assert response.json()["assigned_user_id"] == user["id"]


async def test_unassign_is_idempotent(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Unassign Idempotent Organization",
        slug="unassign-idempotent-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/unassign",
    )

    assert response.status_code == 200
    assert response.json()["assigned_user_id"] is None


async def test_same_status_transition_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Same Status Organization",
        slug="same-status-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "NEW"},
    )

    assert response.status_code == 409


async def test_transition_updates_timestamps(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Transition Timestamp Organization",
        slug="transition-timestamp-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    in_progress = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "IN_PROGRESS"},
    )
    resolved = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "RESOLVED"},
    )
    closed = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "CLOSED"},
    )
    reopened = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "IN_PROGRESS"},
    )

    assert in_progress.status_code == 200
    assert in_progress.json()["resolved_at"] is None
    assert in_progress.json()["closed_at"] is None

    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None
    assert resolved.json()["closed_at"] is None

    assert closed.status_code == 200
    assert closed.json()["resolved_at"] is not None
    assert closed.json()["closed_at"] is not None

    assert reopened.status_code == 200
    assert reopened.json()["resolved_at"] is None
    assert reopened.json()["closed_at"] is None


async def test_invalid_transition_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Transition Organization",
        slug="invalid-transition-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/transition",
        json={"status": "NEW"},
    )

    assert response.status_code == 409


async def test_closed_conversation_blocks_assignment_operations(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Closed Assignment Organization",
        slug="closed-assignment-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="closed-assignment-agent@example.com",
    )
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

    assign_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/assign",
        json={"assigned_user_id": user["id"]},
    )
    unassign_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/unassign",
    )

    assert assign_response.status_code == 409
    assert unassign_response.status_code == 409


async def test_create_with_cross_tenant_contact_returns_404(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Cross Tenant Conversation A",
        slug="cross-tenant-conversation-a",
    )
    organization_b = await create_organization(
        client,
        name="Cross Tenant Conversation B",
        slug="cross-tenant-conversation-b",
    )
    contact_b = await create_contact(client, organization_b["id"])

    response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/conversations",
        json={
            "contact_id": contact_b["id"],
            "subject": "Cross tenant subject",
            "initial_message": "Cross tenant message",
        },
    )

    assert response.status_code == 404


async def test_cross_tenant_user_assignment_returns_404(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Cross Tenant Assignment A",
        slug="cross-tenant-assignment-a",
    )
    organization_b = await create_organization(
        client,
        name="Cross Tenant Assignment B",
        slug="cross-tenant-assignment-b",
    )
    contact_a = await create_contact(client, organization_a["id"])
    user_b = await create_user(
        client,
        organization_b["id"],
        email="cross-tenant-agent@example.com",
    )
    conversation = await create_conversation(
        client,
        organization_a["id"],
        contact_id=str(contact_a["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/conversations/{conversation['id']}/assign",
        json={"assigned_user_id": user_b["id"]},
    )

    assert response.status_code == 404


async def test_inactive_organization_blocks_mutations_but_allows_reads(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Inactive Conversation Organization",
        slug="inactive-conversation-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )
    await deactivate_organization(client, organization["id"])

    get_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
    )
    list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
    )
    create_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={
            "contact_id": contact["id"],
            "subject": "Blocked subject",
            "initial_message": "Blocked message",
        },
    )
    update_response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        json={"subject": "Blocked update"},
    )

    assert get_response.status_code == 200
    assert list_response.status_code == 200
    assert create_response.status_code == 409
    assert update_response.status_code == 409


async def test_inactive_contact_blocks_create(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Inactive Contact Conversation Organization",
        slug="inactive-contact-conversation-organization",
    )
    contact = await create_contact(client, organization["id"])
    await deactivate_contact(client, organization["id"], str(contact["id"]))

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={
            "contact_id": contact["id"],
            "subject": "Inactive contact subject",
            "initial_message": "Inactive contact message",
        },
    )

    assert response.status_code == 409


async def test_inactive_user_blocks_assignment(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Inactive User Conversation Organization",
        slug="inactive-user-conversation-organization",
    )
    contact = await create_contact(client, organization["id"])
    user = await create_user(
        client,
        organization["id"],
        email="inactive-conversation-agent@example.com",
    )
    await deactivate_user(client, organization["id"], str(user["id"]))
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/assign",
        json={"assigned_user_id": user["id"]},
    )

    assert response.status_code == 409


async def test_create_validation_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Validation Organization",
        slug="conversation-validation-organization",
    )
    contact = await create_contact(client, organization["id"])

    responses = [
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations",
            json={
                "subject": "Missing contact",
                "initial_message": "Message",
            },
        ),
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations",
            json={
                "contact_id": contact["id"],
                "subject": "   ",
                "initial_message": "Message",
            },
        ),
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations",
            json={
                "contact_id": contact["id"],
                "subject": "Valid subject",
                "initial_message": "   ",
            },
        ),
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations",
            json={
                "contact_id": contact["id"],
                "subject": "Valid subject",
                "initial_message": "Message",
                "organization_id": organization["id"],
            },
        ),
    ]

    for response in responses:
        assert response.status_code == 422


async def test_update_validation_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Conversation Update Validation Organization",
        slug="conversation-update-validation-organization",
    )
    contact = await create_contact(client, organization["id"])
    conversation = await create_conversation(
        client,
        organization["id"],
        contact_id=str(contact["id"]),
    )

    empty_response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        json={},
    )
    null_subject_response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        json={"subject": None},
    )
    null_priority_response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        json={"priority": None},
    )

    assert empty_response.status_code == 422
    assert null_subject_response.status_code == 422
    assert null_priority_response.status_code == 422


async def test_contradictory_filter_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Contradictory Filter Organization",
        slug="contradictory-filter-organization",
    )
    user = await create_user(
        client,
        organization["id"],
        email="contradictory-filter-agent@example.com",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations"
        f"?unassigned=true&assigned_user_id={user['id']}"
    )

    assert response.status_code == 422


async def test_request_number_unique_with_concurrent_creates() -> None:
    async with isolated_client() as client:
        organization = await create_organization(
            client,
            name="Concurrent Conversation Organization",
            slug="concurrent-conversation-organization",
        )
        contact = await create_contact(client, organization["id"])

        async def create_one(index: int) -> dict[str, Any]:
            response = await client.post(
                f"/api/v1/organizations/{organization['id']}/conversations",
                json={
                    "contact_id": contact["id"],
                    "subject": f"Concurrent subject {index}",
                    "initial_message": f"Concurrent message {index}",
                },
            )
            assert response.status_code == 201
            return cast(dict[str, Any], response.json())

        first, second = await asyncio.gather(
            create_one(1),
            create_one(2),
        )

        assert first["request_number"] != second["request_number"]


async def test_failed_create_rolls_back_aggregate(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.support_request import SupportRequestRepository

    organization = await create_organization(
        client,
        name="Rollback Conversation Organization",
        slug="rollback-conversation-organization",
    )
    contact = await create_contact(client, organization["id"])

    async def broken_create_initial_message(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("message persistence failed")

    monkeypatch.setattr(
        SupportRequestRepository,
        "create_initial_message",
        broken_create_initial_message,
    )

    with pytest.raises(RuntimeError):
        await client.post(
            f"/api/v1/organizations/{organization['id']}/conversations",
            json={
                "contact_id": contact["id"],
                "subject": "Rollback subject",
                "initial_message": "Rollback message",
            },
        )

    monkeypatch.undo()

    list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
    )
    success_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={
            "contact_id": contact["id"],
            "subject": "Successful subject",
            "initial_message": "Successful message",
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert success_response.status_code == 201
