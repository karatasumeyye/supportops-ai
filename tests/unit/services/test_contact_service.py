from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact
from app.models.organization import Organization
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.contact import ContactService


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
    email: str | None = "contact@example.com",
    normalized_email: str | None = "contact@example.com",
    is_active: bool = True,
) -> Contact:
    now = datetime.now(timezone.utc)
    return Contact(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        full_name="Contact Name",
        email=email,
        normalized_email=normalized_email,
        phone="+905551112233",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_service() -> tuple[ContactService, AsyncMock, Mock, Mock]:
    session = AsyncMock()
    service = ContactService(session)
    contact_repository = Mock()
    contact_repository.get_by_normalized_email_and_organization = AsyncMock()
    contact_repository.create = AsyncMock()
    contact_repository.get_by_id_and_organization = AsyncMock()
    contact_repository.list_by_organization = AsyncMock()
    contact_repository.count_by_organization = AsyncMock()
    contact_repository.update = AsyncMock()
    organization_repository = Mock()
    organization_repository.get_by_id = AsyncMock()
    service.contact_repository = contact_repository
    service.organization_repository = organization_repository
    return service, session, contact_repository, organization_repository


async def test_create_contact_normalizes_email_and_commits() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id)
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_normalized_email_and_organization.return_value = None
    contact_repository.create.return_value = contact

    result = await service.create_contact(
        organization.id,
        ContactCreate(
            full_name="Contact Name",
            email="  Contact@Example.COM  ",
            phone="+905551112233",
        ),
    )

    assert result is contact
    contact_repository.get_by_normalized_email_and_organization.assert_awaited_once_with(
        organization.id,
        "contact@example.com",
    )
    contact_repository.create.assert_awaited_once()
    assert contact_repository.create.await_args.kwargs["email"] == "contact@example.com"
    assert (
        contact_repository.create.await_args.kwargs["normalized_email"]
        == "contact@example.com"
    )
    session.commit.assert_awaited_once()


async def test_create_contact_raises_conflict_for_duplicate_email() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_normalized_email_and_organization.return_value = (
        build_contact(organization_id=organization.id)
    )

    with pytest.raises(ConflictError, match="contact@example.com"):
        await service.create_contact(
            organization.id,
            ContactCreate(
                full_name="Contact Name",
                email="contact@example.com",
                phone="+905551112233",
            ),
        )

    contact_repository.create.assert_not_called()
    session.commit.assert_not_awaited()


async def test_get_contact_raises_when_organization_missing() -> None:
    service, _, _, organization_repository = build_service()
    organization_repository.get_by_id.return_value = None
    organization_id = uuid4()

    with pytest.raises(NotFoundError, match=str(organization_id)):
        await service.get_contact(organization_id, uuid4())


async def test_get_contact_raises_when_contact_missing() -> None:
    service, _, contact_repository, organization_repository = build_service()
    organization = build_organization()
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_id_and_organization.return_value = None
    contact_id = uuid4()

    with pytest.raises(NotFoundError, match=str(contact_id)):
        await service.get_contact(organization.id, contact_id)


async def test_list_contacts_normalizes_whitespace_search() -> None:
    service, _, contact_repository, organization_repository = build_service()
    organization = build_organization()
    organization_repository.get_by_id.return_value = organization
    contact_repository.list_by_organization.return_value = []
    contact_repository.count_by_organization.return_value = 0

    result = await service.list_organization_contacts(
        organization.id,
        limit=20,
        offset=0,
        search="   ",
    )

    assert result.total == 0
    assert result.items == []
    assert contact_repository.list_by_organization.await_args.kwargs["search"] is None
    assert contact_repository.count_by_organization.await_args.kwargs["search"] is None


async def test_update_contact_normalizes_email_and_reloads() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id)
    reloaded = build_contact(
        organization_id=organization.id,
        email="new@example.com",
        normalized_email="new@example.com",
    )
    reloaded.id = contact.id
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_id_and_organization.side_effect = [contact, reloaded]
    contact_repository.get_by_normalized_email_and_organization.return_value = None
    contact_repository.update.return_value = contact

    result = await service.update_contact(
        organization.id,
        contact.id,
        ContactUpdate(email="  New@Example.COM  "),
    )

    assert result is reloaded
    assert contact_repository.update.await_args.args[1]["email"] == "new@example.com"
    assert (
        contact_repository.update.await_args.args[1]["normalized_email"]
        == "new@example.com"
    )
    session.commit.assert_awaited_once()


async def test_update_contact_raises_conflict_for_other_contacts_email() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id)
    conflicting_contact = build_contact(organization_id=organization.id)
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_id_and_organization.return_value = contact
    contact_repository.get_by_normalized_email_and_organization.return_value = (
        conflicting_contact
    )

    with pytest.raises(ConflictError, match="Contact email already exists"):
        await service.update_contact(
            organization.id,
            contact.id,
            ContactUpdate(email="different@example.com"),
        )

    contact_repository.update.assert_not_called()
    session.commit.assert_not_awaited()


async def test_update_contact_allows_clearing_email() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id)
    reloaded = build_contact(
        organization_id=organization.id,
        email=None,
        normalized_email=None,
    )
    reloaded.id = contact.id
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_id_and_organization.side_effect = [contact, reloaded]
    contact_repository.update.return_value = contact

    result = await service.update_contact(
        organization.id,
        contact.id,
        ContactUpdate(email=None),
    )

    assert result is reloaded
    assert contact_repository.update.await_args.args[1]["email"] is None
    assert contact_repository.update.await_args.args[1]["normalized_email"] is None
    session.commit.assert_awaited_once()


async def test_deactivate_contact_returns_existing_when_already_inactive() -> None:
    service, session, contact_repository, organization_repository = build_service()
    organization = build_organization()
    contact = build_contact(organization_id=organization.id, is_active=False)
    organization_repository.get_by_id.return_value = organization
    contact_repository.get_by_id_and_organization.return_value = contact

    result = await service.deactivate_contact(organization.id, contact.id)

    assert result is contact
    contact_repository.update.assert_not_called()
    session.commit.assert_not_awaited()


async def test_get_active_organization_raises_conflict_when_inactive() -> None:
    service, _, _, organization_repository = build_service()
    organization = build_organization(is_active=False)
    organization_repository.get_by_id.return_value = organization

    with pytest.raises(ConflictError, match="Organization is inactive"):
        await service._get_active_organization(organization.id)


def test_normalize_email_and_search_helpers() -> None:
    service, _, _, _ = build_service()

    assert service._normalize_email(None) is None
    assert service._normalize_email("  Team@Example.COM  ") == "team@example.com"
    assert service._normalize_search(None) is None
    assert service._normalize_search("   hello  ") == "hello"
    assert service._normalize_search("   ") is None
