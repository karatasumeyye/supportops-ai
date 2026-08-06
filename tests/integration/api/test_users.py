from typing import Any, cast
from uuid import uuid4

from httpx import AsyncClient


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


async def create_user(
    client: AsyncClient,
    organization_id: str,
    *,
    full_name: str = "Jane Doe",
    email: str = "jane.doe@example.com",
    password: str = "strongpass123",
    role: str = "AGENT",
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/organizations/{organization_id}/users",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "role": role,
        },
    )

    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def test_create_owner_user(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Owner Organization",
        slug="owner-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Owner User",
            "email": "owner@example.com",
            "password": "strongpass123",
            "role": "OWNER",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["organization_id"] == organization["id"]
    assert response_data["full_name"] == "Owner User"
    assert response_data["email"] == "owner@example.com"
    assert response_data["role"] == "OWNER"
    assert response_data["is_active"] is True
    assert "id" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data


async def test_create_admin_user(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Admin Organization",
        slug="admin-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Admin User",
            "email": "admin@example.com",
            "password": "strongpass123",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"


async def test_create_agent_user(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Agent Organization",
        slug="agent-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Agent User",
            "email": "agent@example.com",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "AGENT"


async def test_get_user_detail(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Detail Organization",
        slug="detail-organization",
    )
    user = await create_user(
        client,
        organization["id"],
        full_name="Detail User",
        email="detail@example.com",
        role="ADMIN",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/users/{user['id']}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["email"] == "detail@example.com"


async def test_list_organization_users(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="List Organization",
        slug="list-organization",
    )
    other_organization = await create_organization(
        client,
        name="Other Organization",
        slug="other-organization",
    )

    first_user = await create_user(
        client,
        organization["id"],
        full_name="First User",
        email="first@example.com",
        role="OWNER",
    )
    second_user = await create_user(
        client,
        organization["id"],
        full_name="Second User",
        email="second@example.com",
        role="AGENT",
    )
    await create_user(
        client,
        other_organization["id"],
        full_name="Outside User",
        email="outside@example.com",
        role="ADMIN",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/users",
    )

    assert response.status_code == 200

    response_data = response.json()
    returned_ids = {item["id"] for item in response_data}

    assert len(response_data) == 2
    assert returned_ids == {first_user["id"], second_user["id"]}


async def test_update_user(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Update Organization",
        slug="update-organization",
    )
    user = await create_user(
        client,
        organization["id"],
        full_name="Old Name",
        email="old@example.com",
        role="AGENT",
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/users/{user['id']}",
        json={
            "full_name": "New Name",
            "email": "new@example.com",
            "role": "ADMIN",
            "is_active": True,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["full_name"] == "New Name"
    assert response_data["email"] == "new@example.com"
    assert response_data["role"] == "ADMIN"
    assert response_data["is_active"] is True


async def test_deactivate_user(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Deactivate Organization",
        slug="deactivate-organization",
    )
    await create_user(
        client,
        organization["id"],
        full_name="Owner User",
        email="owner-deactivate@example.com",
        role="OWNER",
    )
    user = await create_user(
        client,
        organization["id"],
        full_name="Deactivate Me",
        email="deactivate@example.com",
        role="AGENT",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users/{user['id']}/deactivate",
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_email_is_normalized_to_lowercase(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Normalize Organization",
        slug="normalize-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Normalize User",
            "email": "Normalize.User@Example.COM",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "normalize.user@example.com"


async def test_create_user_with_invalid_email_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Email Organization",
        slug="invalid-email-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Invalid Email User",
            "email": "not-an-email",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 422


async def test_create_user_with_blank_full_name_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Blank Name Organization",
        slug="blank-name-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "",
            "email": "blank@example.com",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 422


async def test_create_user_with_invalid_role_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Role Organization",
        slug="invalid-role-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Invalid Role User",
            "email": "invalid-role@example.com",
            "password": "strongpass123",
            "role": "SUPPORT_AGENT",
        },
    )

    assert response.status_code == 422


async def test_create_user_with_missing_organization_returns_404(
    client: AsyncClient,
) -> None:
    missing_organization_id = "00000000-0000-0000-0000-000000000001"

    response = await client.post(
        f"/api/v1/organizations/{missing_organization_id}/users",
        json={
            "full_name": "Missing Organization User",
            "email": "missing-org@example.com",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Organization not found: {missing_organization_id}"
    )


async def test_invalid_organization_uuid_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/organizations/not-a-valid-uuid/users",
    )

    assert response.status_code == 422


async def test_invalid_user_uuid_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid User UUID Organization",
        slug="invalid-user-uuid-organization",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/users/not-a-valid-uuid",
    )

    assert response.status_code == 422


async def test_create_user_with_invalid_password_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Password Organization",
        slug="invalid-password-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Weak Password User",
            "email": "weak-password@example.com",
            "password": "short",
            "role": "AGENT",
        },
    )

    assert response.status_code == 422


async def test_duplicate_email_in_same_organization_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Duplicate Email Organization",
        slug="duplicate-email-organization",
    )
    await create_user(
        client,
        organization["id"],
        full_name="First User",
        email="duplicate@example.com",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Second User",
            "email": "duplicate@example.com",
            "password": "strongpass123",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "User email already exists: duplicate@example.com"
    )


async def test_duplicate_email_in_different_organization_returns_409(
    client: AsyncClient,
) -> None:
    first_organization = await create_organization(
        client,
        name="First Duplicate Organization",
        slug="first-duplicate-organization",
    )
    second_organization = await create_organization(
        client,
        name="Second Duplicate Organization",
        slug="second-duplicate-organization",
    )
    await create_user(
        client,
        first_organization["id"],
        full_name="First User",
        email="global@example.com",
    )

    response = await client.post(
        f"/api/v1/organizations/{second_organization['id']}/users",
        json={
            "full_name": "Second User",
            "email": "global@example.com",
            "password": "strongpass123",
            "role": "OWNER",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "User email already exists: global@example.com"
    )


async def test_case_insensitive_duplicate_email_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Case Duplicate Organization",
        slug="case-duplicate-organization",
    )
    await create_user(
        client,
        organization["id"],
        full_name="First User",
        email="Case.User@Example.com",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users",
        json={
            "full_name": "Second User",
            "email": "case.user@example.com",
            "password": "strongpass123",
            "role": "AGENT",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "User email already exists: case.user@example.com"
    )


async def test_cannot_get_user_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Tenant A",
        slug="tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Tenant B",
        slug="tenant-b",
    )
    user_b = await create_user(
        client,
        organization_b["id"],
        full_name="Tenant B User",
        email="tenant-b-user@example.com",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization_a['id']}/users/{user_b['id']}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"User not found: {user_b['id']}"


async def test_cannot_update_user_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Update Tenant A",
        slug="update-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Update Tenant B",
        slug="update-tenant-b",
    )
    user_b = await create_user(
        client,
        organization_b["id"],
        full_name="Tenant B User",
        email="update-tenant-b-user@example.com",
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization_a['id']}/users/{user_b['id']}",
        json={
            "full_name": "Hacked Name",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"User not found: {user_b['id']}"


async def test_cannot_deactivate_user_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Deactivate Tenant A",
        slug="deactivate-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Deactivate Tenant B",
        slug="deactivate-tenant-b",
    )
    user_b = await create_user(
        client,
        organization_b["id"],
        full_name="Tenant B User",
        email="deactivate-tenant-b-user@example.com",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/users/{user_b['id']}/deactivate",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"User not found: {user_b['id']}"


async def test_list_users_returns_only_requested_organization_users(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="List Tenant A",
        slug="list-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="List Tenant B",
        slug="list-tenant-b",
    )
    user_a = await create_user(
        client,
        organization_a["id"],
        full_name="Tenant A User",
        email="tenant-a-user@example.com",
    )
    await create_user(
        client,
        organization_b["id"],
        full_name="Tenant B User",
        email="tenant-b-user@example.com",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization_a['id']}/users",
    )

    assert response.status_code == 200

    response_data = cast(list[dict[str, Any]], response.json())

    assert len(response_data) == 1
    assert response_data[0]["id"] == user_a["id"]


async def test_last_active_owner_cannot_be_deactivated(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Last Owner Organization",
        slug="last-owner-organization",
    )
    owner = await create_user(
        client,
        organization["id"],
        full_name="Only Owner",
        email="only-owner@example.com",
        role="OWNER",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users/{owner['id']}/deactivate",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Last active owner cannot be deactivated or demoted."
    )


async def test_one_owner_can_be_deactivated_when_multiple_owners_exist(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Multiple Owners Organization",
        slug="multiple-owners-organization",
    )
    first_owner = await create_user(
        client,
        organization["id"],
        full_name="First Owner",
        email="first-owner@example.com",
        role="OWNER",
    )
    await create_user(
        client,
        organization["id"],
        full_name="Second Owner",
        email="second-owner@example.com",
        role="OWNER",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/users/{first_owner['id']}/deactivate",
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_last_owner_cannot_be_demoted_to_admin(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Demote Owner Organization",
        slug="demote-owner-organization",
    )
    owner = await create_user(
        client,
        organization["id"],
        full_name="Only Owner",
        email="demote-owner@example.com",
        role="OWNER",
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/users/{owner['id']}",
        json={
            "role": "ADMIN",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Last active owner cannot be deactivated or demoted."
    )


async def test_get_nonexistent_user_returns_404(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Nonexistent User Organization",
        slug="nonexistent-user-organization",
    )
    user_id = str(uuid4())

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/users/{user_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"User not found: {user_id}"
