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


async def deactivate_organization(
    client: AsyncClient,
    organization_id: str,
) -> dict[str, object]:
    response = await client.patch(
        f"/api/v1/organizations/{organization_id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    return cast(dict[str, object], response.json())


async def create_contact(
    client: AsyncClient,
    organization_id: str,
    *,
    full_name: str = "Jane Contact",
    email: str | None = "jane.contact@example.com",
    phone: str | None = "+905321112233",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": full_name,
    }
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


async def test_create_contact_with_email_and_phone(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Contact Organization",
        slug="contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Ahmet Yilmaz",
            "email": "ahmet@example.com",
            "phone": "+905321234567",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["organization_id"] == organization["id"]
    assert response_data["full_name"] == "Ahmet Yilmaz"
    assert response_data["email"] == "ahmet@example.com"
    assert response_data["phone"] == "+905321234567"
    assert response_data["is_active"] is True
    assert "id" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data


async def test_create_contact_with_only_email(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Email Contact Organization",
        slug="email-contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Email Only Contact",
            "email": "email-only@example.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "email-only@example.com"
    assert response.json()["phone"] is None


async def test_create_contact_with_only_phone(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Phone Contact Organization",
        slug="phone-contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Phone Only Contact",
            "phone": "+905329998877",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] is None
    assert response.json()["phone"] == "+905329998877"


async def test_contact_email_is_normalized(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Normalize Contact Organization",
        slug="normalize-contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Normalize Contact",
            "email": "  Normalize.Contact@Example.COM  ",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "normalize.contact@example.com"


async def test_get_contact_detail(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Detail Contact Organization",
        slug="detail-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Detail Contact",
        email="detail-contact@example.com",
        phone=None,
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == contact["id"]
    assert response.json()["full_name"] == "Detail Contact"


async def test_list_contacts_uses_default_pagination(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Pagination Contact Organization",
        slug="pagination-contact-organization",
    )

    for index in range(25):
        await create_contact(
            client,
            organization["id"],
            full_name=f"Contact {index}",
            email=f"contact{index}@example.com",
            phone=None,
        )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts",
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert response_data["total"] == 25
    assert len(response_data["items"]) == 20


async def test_list_contacts_with_offset(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Offset Contact Organization",
        slug="offset-contact-organization",
    )

    for index in range(5):
        await create_contact(
            client,
            organization["id"],
            full_name=f"Offset Contact {index}",
            email=f"offset{index}@example.com",
            phone=None,
        )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?limit=2&offset=2",
    )

    assert response.status_code == 200
    assert response.json()["limit"] == 2
    assert response.json()["offset"] == 2
    assert len(response.json()["items"]) == 2


async def test_list_contacts_filters_by_active_state(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Active Filter Organization",
        slug="active-filter-organization",
    )
    active_contact = await create_contact(
        client,
        organization["id"],
        full_name="Active Contact",
        email="active@example.com",
        phone=None,
    )
    inactive_contact = await create_contact(
        client,
        organization["id"],
        full_name="Inactive Contact",
        email="inactive@example.com",
        phone=None,
    )
    deactivate_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts/{inactive_contact['id']}/deactivate",
    )
    assert deactivate_response.status_code == 200

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?is_active=true",
    )

    assert response.status_code == 200

    response_data = response.json()
    returned_ids = {item["id"] for item in response_data["items"]}

    assert response_data["total"] == 1
    assert returned_ids == {active_contact["id"]}


async def test_list_contacts_searches_by_name_email_and_phone(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Search Contact Organization",
        slug="search-contact-organization",
    )
    name_contact = await create_contact(
        client,
        organization["id"],
        full_name="Ahmet Search",
        email="ahmet-search@example.com",
        phone=None,
    )
    email_contact = await create_contact(
        client,
        organization["id"],
        full_name="Email Match",
        email="customer.match@example.com",
        phone=None,
    )
    phone_contact = await create_contact(
        client,
        organization["id"],
        full_name="Phone Match",
        email="phone-match@example.com",
        phone="+905300001122",
    )

    name_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?search=ahmet",
    )
    email_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?search=customer.match",
    )
    phone_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?search=1122",
    )

    assert name_response.status_code == 200
    assert email_response.status_code == 200
    assert phone_response.status_code == 200

    assert name_response.json()["items"][0]["id"] == name_contact["id"]
    assert email_response.json()["items"][0]["id"] == email_contact["id"]
    assert phone_response.json()["items"][0]["id"] == phone_contact["id"]


async def test_list_contacts_returns_empty_items_when_search_has_no_match(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Empty Search Organization",
        slug="empty-search-organization",
    )
    await create_contact(
        client,
        organization["id"],
        full_name="Existing Contact",
        email="existing-contact@example.com",
        phone=None,
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts?search=not-found",
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


async def test_update_contact(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Update Contact Organization",
        slug="update-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Old Contact",
        email="old-contact@example.com",
        phone="+905300000001",
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
        json={
            "full_name": "New Contact",
            "email": "new-contact@example.com",
            "phone": "+905300000002",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["full_name"] == "New Contact"
    assert response_data["email"] == "new-contact@example.com"
    assert response_data["phone"] == "+905300000002"


async def test_update_contact_can_clear_email(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Clear Email Contact Organization",
        slug="clear-email-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Clear Email Contact",
        email="clear-contact@example.com",
        phone="+905399991122",
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
        json={"email": None},
    )

    assert response.status_code == 200
    assert response.json()["email"] is None


async def test_deactivate_contact_is_idempotent(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Deactivate Contact Organization",
        slug="deactivate-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Deactivate Contact",
        email="deactivate-contact@example.com",
        phone=None,
    )

    first_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}/deactivate",
    )
    second_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}/deactivate",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["is_active"] is False
    assert second_response.json()["is_active"] is False


async def test_create_contact_requires_email_or_phone(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Required Contact Method Organization",
        slug="required-contact-method-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={"full_name": "No Contact Method"},
    )

    assert response.status_code == 422


async def test_create_contact_with_invalid_email_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Contact Email Organization",
        slug="invalid-contact-email-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Invalid Contact Email",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422


async def test_create_contact_with_blank_full_name_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Blank Contact Name Organization",
        slug="blank-contact-name-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "",
            "email": "blank-contact@example.com",
        },
    )

    assert response.status_code == 422


async def test_create_contact_with_whitespace_full_name_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Whitespace Contact Name Organization",
        slug="whitespace-contact-name-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "   ",
            "email": "whitespace-contact@example.com",
        },
    )

    assert response.status_code == 422


async def test_create_contact_with_too_long_phone_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Long Phone Contact Organization",
        slug="long-phone-contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Long Phone Contact",
            "phone": "1" * 33,
        },
    )

    assert response.status_code == 422


async def test_invalid_contact_uuid_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Invalid Contact UUID Organization",
        slug="invalid-contact-uuid-organization",
    )

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts/not-a-valid-uuid",
    )

    assert response.status_code == 422


async def test_unknown_contact_field_returns_422(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Unknown Field Contact Organization",
        slug="unknown-field-contact-organization",
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Unknown Field Contact",
            "email": "unknown-field@example.com",
            "unknown_field": "unexpected",
        },
    )

    assert response.status_code == 422


async def test_duplicate_contact_email_in_same_organization_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Duplicate Contact Email Organization",
        slug="duplicate-contact-email-organization",
    )
    await create_contact(
        client,
        organization["id"],
        full_name="First Contact",
        email="duplicate-contact@example.com",
        phone=None,
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Second Contact",
            "email": "duplicate-contact@example.com",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Contact email already exists: duplicate-contact@example.com"
    )


async def test_case_insensitive_duplicate_contact_email_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Case Duplicate Contact Organization",
        slug="case-duplicate-contact-organization",
    )
    await create_contact(
        client,
        organization["id"],
        full_name="First Contact",
        email="Case.Contact@Example.com",
        phone=None,
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Second Contact",
            "email": "case.contact@example.com",
        },
    )

    assert response.status_code == 409


async def test_whitespace_variant_duplicate_contact_email_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Whitespace Duplicate Contact Organization",
        slug="whitespace-duplicate-contact-organization",
    )
    await create_contact(
        client,
        organization["id"],
        full_name="First Contact",
        email="trimmed.contact@example.com",
        phone=None,
    )

    response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Second Contact",
            "email": "  trimmed.contact@example.com  ",
        },
    )

    assert response.status_code == 409


async def test_update_contact_to_existing_email_returns_409(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Update Duplicate Contact Organization",
        slug="update-duplicate-contact-organization",
    )
    first_contact = await create_contact(
        client,
        organization["id"],
        full_name="First Contact",
        email="first-duplicate@example.com",
        phone=None,
    )
    second_contact = await create_contact(
        client,
        organization["id"],
        full_name="Second Contact",
        email="second-duplicate@example.com",
        phone=None,
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/contacts/{second_contact['id']}",
        json={"email": "first-duplicate@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Contact email already exists: first-duplicate@example.com"
    )
    assert first_contact["id"] != second_contact["id"]


async def test_update_contact_with_same_email_succeeds(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Same Email Update Contact Organization",
        slug="same-email-update-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Same Email Contact",
        email="same-email@example.com",
        phone=None,
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
        json={"email": "same-email@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "same-email@example.com"


async def test_same_email_in_different_organizations_is_allowed(
    client: AsyncClient,
) -> None:
    first_organization = await create_organization(
        client,
        name="First Shared Contact Organization",
        slug="first-shared-contact-organization",
    )
    second_organization = await create_organization(
        client,
        name="Second Shared Contact Organization",
        slug="second-shared-contact-organization",
    )

    first_contact = await create_contact(
        client,
        first_organization["id"],
        full_name="Shared Contact A",
        email="shared-contact@example.com",
        phone=None,
    )
    second_contact = await create_contact(
        client,
        second_organization["id"],
        full_name="Shared Contact B",
        email="shared-contact@example.com",
        phone=None,
    )

    assert first_contact["id"] != second_contact["id"]


async def test_cannot_get_contact_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Contact Tenant A",
        slug="contact-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Contact Tenant B",
        slug="contact-tenant-b",
    )
    contact_b = await create_contact(
        client,
        organization_b["id"],
        full_name="Tenant B Contact",
        email="tenant-b-contact@example.com",
        phone=None,
    )

    response = await client.get(
        f"/api/v1/organizations/{organization_a['id']}/contacts/{contact_b['id']}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Contact not found: {contact_b['id']}"


async def test_cannot_update_contact_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Update Contact Tenant A",
        slug="update-contact-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Update Contact Tenant B",
        slug="update-contact-tenant-b",
    )
    contact_b = await create_contact(
        client,
        organization_b["id"],
        full_name="Tenant B Contact",
        email="update-tenant-b-contact@example.com",
        phone=None,
    )

    response = await client.patch(
        f"/api/v1/organizations/{organization_a['id']}/contacts/{contact_b['id']}",
        json={"full_name": "Updated Wrong Tenant"},
    )

    assert response.status_code == 404


async def test_cannot_deactivate_contact_from_different_organization(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="Deactivate Contact Tenant A",
        slug="deactivate-contact-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="Deactivate Contact Tenant B",
        slug="deactivate-contact-tenant-b",
    )
    contact_b = await create_contact(
        client,
        organization_b["id"],
        full_name="Tenant B Contact",
        email="deactivate-tenant-b-contact@example.com",
        phone=None,
    )

    response = await client.post(
        f"/api/v1/organizations/{organization_a['id']}/contacts/{contact_b['id']}/deactivate",
    )

    assert response.status_code == 404


async def test_list_contacts_returns_only_requested_organization_contacts(
    client: AsyncClient,
) -> None:
    organization_a = await create_organization(
        client,
        name="List Contact Tenant A",
        slug="list-contact-tenant-a",
    )
    organization_b = await create_organization(
        client,
        name="List Contact Tenant B",
        slug="list-contact-tenant-b",
    )
    contact_a = await create_contact(
        client,
        organization_a["id"],
        full_name="Tenant A Contact",
        email="tenant-a-contact@example.com",
        phone=None,
    )
    await create_contact(
        client,
        organization_b["id"],
        full_name="Tenant B Contact",
        email="tenant-b-contact@example.com",
        phone=None,
    )

    response = await client.get(
        f"/api/v1/organizations/{organization_a['id']}/contacts",
    )

    assert response.status_code == 200

    response_data = cast(dict[str, Any], response.json())

    assert response_data["total"] == 1
    assert response_data["items"][0]["id"] == contact_a["id"]


async def test_create_contact_with_missing_organization_returns_404(
    client: AsyncClient,
) -> None:
    missing_organization_id = "00000000-0000-0000-0000-000000000001"

    response = await client.post(
        f"/api/v1/organizations/{missing_organization_id}/contacts",
        json={
            "full_name": "Missing Contact Organization",
            "email": "missing-contact-org@example.com",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Organization not found: {missing_organization_id}"
    )


async def test_inactive_organization_blocks_contact_mutations_but_allows_reads(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Inactive Contact Organization",
        slug="inactive-contact-organization",
    )
    contact = await create_contact(
        client,
        organization["id"],
        full_name="Inactive Organization Contact",
        email="inactive-organization-contact@example.com",
        phone=None,
    )
    await deactivate_organization(client, organization["id"])

    get_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
    )
    list_response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts",
    )
    create_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts",
        json={
            "full_name": "Blocked Contact",
            "email": "blocked-contact@example.com",
        },
    )
    update_response = await client.patch(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}",
        json={"full_name": "Blocked Update"},
    )
    deactivate_response = await client.post(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact['id']}/deactivate",
    )

    assert get_response.status_code == 200
    assert list_response.status_code == 200
    assert create_response.status_code == 409
    assert update_response.status_code == 409
    assert deactivate_response.status_code == 409
    assert create_response.json()["detail"] == (
        f"Organization is inactive: {organization['id']}"
    )


async def test_get_nonexistent_contact_returns_404(
    client: AsyncClient,
) -> None:
    organization = await create_organization(
        client,
        name="Nonexistent Contact Organization",
        slug="nonexistent-contact-organization",
    )
    contact_id = str(uuid4())

    response = await client.get(
        f"/api/v1/organizations/{organization['id']}/contacts/{contact_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Contact not found: {contact_id}"
