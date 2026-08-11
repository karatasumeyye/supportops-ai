from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.organization import OrganizationService


def build_organization(
    *,
    name: str = "SupportOps",
    slug: str = "supportops",
    is_active: bool = True,
) -> Organization:
    now = datetime.now(timezone.utc)
    return Organization(
        id=uuid4(),
        name=name,
        slug=slug,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_service() -> tuple[OrganizationService, AsyncMock, Mock]:
    session = AsyncMock()
    service = OrganizationService(session)
    repository = Mock()
    repository.get_by_slug = AsyncMock()
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.list_all = AsyncMock()
    repository.update = AsyncMock()
    service.repository = repository
    return service, session, repository


async def test_create_generates_slug_when_missing() -> None:
    service, session, repository = build_service()
    organization = build_organization(slug="my-team")
    repository.get_by_slug.return_value = None
    repository.create.return_value = organization

    payload = OrganizationCreate(name="My Team", slug=None)
    result = await service.create(payload)

    assert result is organization
    repository.get_by_slug.assert_awaited_once_with("my-team")
    repository.create.assert_awaited_once()
    created_payload = repository.create.await_args.args[0]
    assert isinstance(created_payload, OrganizationCreate)
    assert created_payload.slug == "my-team"
    session.commit.assert_awaited_once()


async def test_create_raises_conflict_when_generated_slug_exists() -> None:
    service, session, repository = build_service()
    repository.get_by_slug.return_value = build_organization(slug="my-team")

    with pytest.raises(ConflictError, match="Organization slug already exists"):
        await service.create(OrganizationCreate(name="My Team", slug=None))

    repository.create.assert_not_called()
    session.commit.assert_not_awaited()


async def test_create_raises_conflict_when_explicit_slug_exists() -> None:
    service, session, repository = build_service()
    repository.get_by_slug.return_value = build_organization(slug="custom-team")

    with pytest.raises(ConflictError, match="custom-team"):
        await service.create(OrganizationCreate(name="My Team", slug="custom-team"))

    repository.create.assert_not_called()
    session.commit.assert_not_awaited()


async def test_get_by_id_returns_organization() -> None:
    service, _, repository = build_service()
    organization = build_organization()
    repository.get_by_id.return_value = organization

    result = await service.get_by_id(organization.id)

    assert result is organization


async def test_get_by_id_raises_not_found() -> None:
    service, _, repository = build_service()
    organization_id = uuid4()
    repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match=str(organization_id)):
        await service.get_by_id(organization_id)


async def test_list_all_returns_repository_results() -> None:
    service, _, repository = build_service()
    organizations = [build_organization(), build_organization(slug="ops-team")]
    repository.list_all.return_value = organizations

    result = await service.list_all()

    assert result == organizations


async def test_update_reloads_updated_organization() -> None:
    service, session, repository = build_service()
    organization = build_organization(slug="old-slug")
    reloaded = build_organization(slug="new-slug")
    reloaded.id = organization.id
    repository.get_by_id.side_effect = [organization, reloaded]
    repository.get_by_slug.return_value = None
    repository.update.return_value = organization

    result = await service.update(
        organization.id,
        OrganizationUpdate(name="Updated Name", slug="new-slug"),
    )

    assert result is reloaded
    repository.get_by_slug.assert_awaited_once_with("new-slug")
    session.commit.assert_awaited_once()


async def test_update_skips_slug_lookup_when_slug_unchanged() -> None:
    service, session, repository = build_service()
    organization = build_organization(slug="same-slug")
    repository.get_by_id.side_effect = [organization, organization]
    repository.update.return_value = organization

    result = await service.update(
        organization.id,
        OrganizationUpdate(name="Updated Name", slug="same-slug"),
    )

    assert result is organization
    repository.get_by_slug.assert_not_called()
    session.commit.assert_awaited_once()


async def test_update_raises_conflict_when_new_slug_exists() -> None:
    service, session, repository = build_service()
    organization = build_organization(slug="old-slug")
    repository.get_by_id.return_value = organization
    repository.get_by_slug.return_value = build_organization(slug="new-slug")

    with pytest.raises(ConflictError, match="new-slug"):
        await service.update(
            organization.id,
            OrganizationUpdate(name="Updated Name", slug="new-slug"),
        )

    repository.update.assert_not_called()
    session.commit.assert_not_awaited()


def test_generate_slug_falls_back_to_default() -> None:
    service, _, _ = build_service()

    assert service._generate_slug("!!!") == "organization"
