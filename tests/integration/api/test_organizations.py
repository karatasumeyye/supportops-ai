from httpx import AsyncClient


async def test_create_organization(client: AsyncClient,) -> None:

    response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Acme Support",
            "slug": "acme-support",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Acme Support"
    assert response_data["slug"] == "acme-support"
    assert "id" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data


async def test_list_organizations(client: AsyncClient,) -> None:

    create_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Support Company",
            "slug": "support-company",
        },
    )

    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/organizations",
    )

    assert response.status_code == 200

    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Support Company"
    assert response_data[0]["slug"] == "support-company"


async def test_get_organization_by_id(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Example Organization",
            "slug": "example-organization",
        },
    )

    assert create_response.status_code == 201

    organization_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/organizations/{organization_id}",
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == organization_id
    assert response_data["name"] == "Example Organization"
    assert response_data["slug"] == "example-organization"


async def test_update_organization_name(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Old Organization Name",
            "slug": "organization-name-test",
        },
    )

    assert create_response.status_code == 201

    organization_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/organizations/{organization_id}",
        json={
            "name": "New Organization Name",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["name"] == "New Organization Name"
    assert response_data["slug"] == "organization-name-test"


async def test_update_organization_slug(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Slug Test Organization",
            "slug": "old-organization-slug",
        },
    )

    assert create_response.status_code == 201

    organization_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/organizations/{organization_id}",
        json={
            "slug": "new-organization-slug",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["name"] == "Slug Test Organization"
    assert response_data["slug"] == "new-organization-slug"


async def test_update_organization_with_existing_slug_returns_409(
    client: AsyncClient,
) -> None:
    first_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "First Organization",
            "slug": "first-organization",
        },
    )

    second_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Second Organization",
            "slug": "second-organization",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    second_organization_id = second_response.json()["id"]

    response = await client.patch(
        f"/api/v1/organizations/{second_organization_id}",
        json={
            "slug": "first-organization",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Organization slug already exists: first-organization"
    )


async def test_get_nonexistent_organization_returns_404(client: AsyncClient,) -> None:

    response = await client.get(
        "/api/v1/organizations/"
        "00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Organization not found: "
        "00000000-0000-0000-0000-000000000001"
    )


async def test_invalid_organization_id_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/organizations/not-a-valid-uuid",
    )

    assert response.status_code == 422


async def test_duplicate_slug_returns_409(client: AsyncClient,) -> None:

    payload = {
        "name": "Acme Support",
        "slug": "duplicate-slug",
    }

    first_response = await client.post(
        "/api/v1/organizations",
        json=payload,
    )

    second_response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Another Organization",
            "slug": "duplicate-slug",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Organization slug already exists: duplicate-slug"
    )


async def test_create_organization_with_missing_name_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/organizations",
        json={
            "slug": "missing-name",
        },
    )

    assert response.status_code == 422


async def test_create_organization_with_invalid_slug_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Invalid Slug Organization",
            "slug": "Invalid Slug!",
        },
    )

    assert response.status_code == 422
