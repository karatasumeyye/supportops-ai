from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact
from app.models.enums import SupportRequestStatus, UserRole
from app.models.organization import Organization
from app.models.support_request import SupportRequest
from app.models.user import User
from app.services.support_request import SupportRequestService


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
    assigned_user_id: UUID | None = None,
    status: SupportRequestStatus = SupportRequestStatus.NEW,
    resolved_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> SupportRequest:
    now = datetime.now(timezone.utc)
    return SupportRequest(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        contact_id=contact_id or uuid4(),
        assigned_user_id=assigned_user_id,
        request_number="CONV-000001",
        subject="Need help",
        status=status,
        priority="MEDIUM",
        resolved_at=resolved_at,
        closed_at=closed_at,
        created_at=now,
        updated_at=now,
    )


def build_service() -> tuple[SupportRequestService, AsyncMock, Mock, Mock, Mock, Mock]:
    session = AsyncMock()
    service = SupportRequestService(session)
    support_request_repository = Mock()
    support_request_repository.get_by_id_and_organization = AsyncMock()
    support_request_repository.update = AsyncMock()
    contact_repository = Mock()
    contact_repository.get_by_id_and_organization = AsyncMock()
    organization_repository = Mock()
    organization_repository.get_by_id = AsyncMock()
    user_repository = Mock()
    user_repository.get_by_id_and_organization = AsyncMock()
    service.support_request_repository = support_request_repository
    service.contact_repository = contact_repository
    service.organization_repository = organization_repository
    service.user_repository = user_repository
    return (
        service,
        session,
        support_request_repository,
        contact_repository,
        organization_repository,
        user_repository,
    )


def test_normalize_search_helper() -> None:
    service, _, _, _, _, _ = build_service()

    assert service._normalize_search(None) is None
    assert service._normalize_search("   ") is None
    assert service._normalize_search("  billing  ") == "billing"


def test_build_transition_updates_for_resolved_to_closed_preserves_resolved_at() -> (
    None
):
    service, _, _, _, _, _ = build_service()
    resolved_at = datetime.now(timezone.utc)
    support_request = build_support_request(
        status=SupportRequestStatus.RESOLVED,
        resolved_at=resolved_at,
    )

    updates = service._build_transition_updates(
        support_request=support_request,
        target_status=SupportRequestStatus.CLOSED,
    )

    assert updates["status"] == SupportRequestStatus.CLOSED
    assert updates["resolved_at"] == resolved_at
    assert updates["closed_at"] is not None


def test_build_transition_updates_for_in_progress_clears_timestamps() -> None:
    service, _, _, _, _, _ = build_service()
    support_request = build_support_request(
        status=SupportRequestStatus.CLOSED,
        resolved_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
    )

    updates = service._build_transition_updates(
        support_request=support_request,
        target_status=SupportRequestStatus.IN_PROGRESS,
    )

    assert updates == {
        "status": SupportRequestStatus.IN_PROGRESS,
        "resolved_at": None,
        "closed_at": None,
    }


async def test_get_assignable_user_returns_none_when_not_provided() -> None:
    service, _, _, _, _, user_repository = build_service()

    result = await service._get_assignable_user(uuid4(), None)

    assert result is None
    user_repository.get_by_id_and_organization.assert_not_called()


async def test_get_assignable_user_raises_not_found_for_missing_user() -> None:
    service, _, _, _, _, user_repository = build_service()
    user_id = uuid4()
    user_repository.get_by_id_and_organization.return_value = None

    with pytest.raises(NotFoundError, match=str(user_id)):
        await service._get_assignable_user(uuid4(), user_id)


async def test_get_assignable_user_raises_conflict_for_inactive_user() -> None:
    service, _, _, _, _, user_repository = build_service()
    user = build_user(is_active=False)
    user_repository.get_by_id_and_organization.return_value = user

    with pytest.raises(ConflictError, match="User is inactive"):
        await service._get_assignable_user(uuid4(), user.id)


async def test_get_assignable_user_raises_conflict_for_ineligible_role() -> None:
    service, _, _, _, _, user_repository = build_service()
    user = build_user(role=Mock())
    user_repository.get_by_id_and_organization.return_value = user

    with pytest.raises(ConflictError, match="User role is not assignable"):
        await service._get_assignable_user(uuid4(), user.id)


async def test_get_contact_for_create_raises_not_found_for_missing_contact() -> None:
    service, _, _, contact_repository, _, _ = build_service()
    contact_id = uuid4()
    contact_repository.get_by_id_and_organization.return_value = None

    with pytest.raises(NotFoundError, match=str(contact_id)):
        await service._get_contact_for_create(uuid4(), contact_id)


async def test_get_contact_for_create_raises_conflict_for_inactive_contact() -> None:
    service, _, _, contact_repository, _, _ = build_service()
    contact = build_contact(is_active=False)
    contact_repository.get_by_id_and_organization.return_value = contact

    with pytest.raises(ConflictError, match="Contact is inactive"):
        await service._get_contact_for_create(uuid4(), contact.id)


async def test_get_active_organization_raises_conflict_when_inactive() -> None:
    service, _, _, _, organization_repository, _ = build_service()
    organization_repository.get_by_id.return_value = build_organization(is_active=False)

    with pytest.raises(ConflictError, match="Organization is inactive"):
        await service._get_active_organization(uuid4())


async def test_transition_support_request_raises_for_same_status() -> None:
    service, _, support_request_repository, _, organization_repository, _ = (
        build_service()
    )
    organization = build_organization()
    support_request = build_support_request(
        organization_id=organization.id,
        status=SupportRequestStatus.NEW,
    )
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = support_request

    with pytest.raises(ConflictError, match="already in status"):
        await service.transition_support_request(
            organization.id,
            support_request.id,
            SupportRequestStatus.NEW,
        )


async def test_assign_support_request_returns_existing_when_same_user_assigned() -> (
    None
):
    (
        service,
        session,
        support_request_repository,
        _,
        organization_repository,
        user_repository,
    ) = build_service()
    organization = build_organization()
    user = build_user(organization_id=organization.id)
    support_request = build_support_request(
        organization_id=organization.id,
        assigned_user_id=user.id,
        status=SupportRequestStatus.IN_PROGRESS,
    )
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = support_request
    user_repository.get_by_id_and_organization.return_value = user

    result = await service.assign_support_request(
        organization.id,
        support_request.id,
        user.id,
    )

    assert result is support_request
    support_request_repository.update.assert_not_called()
    session.commit.assert_not_awaited()


async def test_unassign_support_request_returns_existing_when_already_unassigned() -> (
    None
):
    service, session, support_request_repository, _, organization_repository, _ = (
        build_service()
    )
    organization = build_organization()
    support_request = build_support_request(
        organization_id=organization.id,
        assigned_user_id=None,
        status=SupportRequestStatus.IN_PROGRESS,
    )
    organization_repository.get_by_id.return_value = organization
    support_request_repository.get_by_id_and_organization.return_value = support_request

    result = await service.unassign_support_request(
        organization.id,
        support_request.id,
    )

    assert result is support_request
    support_request_repository.update.assert_not_called()
    session.commit.assert_not_awaited()
