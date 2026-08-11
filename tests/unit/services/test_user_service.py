from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import UserService


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


def build_user(
    *,
    organization_id: UUID | None = None,
    email: str = "agent@example.com",
    normalized_email: str = "agent@example.com",
    role: UserRole = UserRole.AGENT,
    is_active: bool = True,
) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        full_name="Agent User",
        email=email,
        normalized_email=normalized_email,
        password_hash="existing-hash",
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def build_service() -> tuple[UserService, AsyncMock, Mock, Mock]:
    session = AsyncMock()
    service = UserService(session)
    user_repository = Mock()
    user_repository.get_by_email = AsyncMock()
    user_repository.create = AsyncMock()
    user_repository.get_by_id_and_organization = AsyncMock()
    user_repository.list_by_organization = AsyncMock()
    user_repository.update = AsyncMock()
    user_repository.count_active_owners = AsyncMock()
    organization_repository = Mock()
    organization_repository.get_by_id = AsyncMock()
    service.user_repository = user_repository
    service.organization_repository = organization_repository
    return service, session, user_repository, organization_repository


async def test_create_user_normalizes_email_hashes_password_and_commits() -> None:
    service, session, user_repository, organization_repository = build_service()
    organization = build_organization()
    user = build_user(organization_id=organization.id)
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_email.return_value = None
    user_repository.create.return_value = user

    result = await service.create_user(
        organization.id,
        UserCreate(
            full_name="Agent User",
            email="  Agent@Example.COM  ",
            password="strongpass123",
            role=UserRole.AGENT,
        ),
    )

    assert result is user
    user_repository.get_by_email.assert_awaited_once_with("agent@example.com")
    create_kwargs = user_repository.create.await_args.kwargs
    assert create_kwargs["email"] == "agent@example.com"
    assert create_kwargs["normalized_email"] == "agent@example.com"
    assert create_kwargs["password_hash"] != "strongpass123"
    assert create_kwargs["password_hash"].startswith("pbkdf2_sha256$")
    session.commit.assert_awaited_once()


async def test_create_user_raises_conflict_for_duplicate_email() -> None:
    service, session, user_repository, organization_repository = build_service()
    organization = build_organization()
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_email.return_value = build_user(
        organization_id=organization.id
    )

    with pytest.raises(ConflictError, match="User email already exists"):
        await service.create_user(
            organization.id,
            UserCreate(
                full_name="Agent User",
                email="agent@example.com",
                password="strongpass123",
                role=UserRole.AGENT,
            ),
        )

    user_repository.create.assert_not_called()
    session.commit.assert_not_awaited()


async def test_get_user_raises_when_organization_missing() -> None:
    service, _, _, organization_repository = build_service()
    organization_repository.get_by_id.return_value = None
    organization_id = uuid4()

    with pytest.raises(NotFoundError, match=str(organization_id)):
        await service.get_user(organization_id, uuid4())


async def test_get_user_raises_when_user_missing() -> None:
    service, _, user_repository, organization_repository = build_service()
    organization = build_organization()
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_id_and_organization.return_value = None
    user_id = uuid4()

    with pytest.raises(NotFoundError, match=str(user_id)):
        await service.get_user(organization.id, user_id)


async def test_list_users_returns_repository_values() -> None:
    service, _, user_repository, organization_repository = build_service()
    organization = build_organization()
    users = [build_user(organization_id=organization.id)]
    organization_repository.get_by_id.return_value = organization
    user_repository.list_by_organization.return_value = users

    result = await service.list_organization_users(organization.id)

    assert result == users


async def test_update_user_normalizes_email_hashes_password_and_reloads() -> None:
    service, session, user_repository, organization_repository = build_service()
    organization = build_organization()
    user = build_user(organization_id=organization.id)
    reloaded = build_user(
        organization_id=organization.id,
        email="new@example.com",
        normalized_email="new@example.com",
    )
    reloaded.id = user.id
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_id_and_organization.side_effect = [user, reloaded]
    user_repository.get_by_email.return_value = None
    user_repository.update.return_value = user

    result = await service.update_user(
        organization.id,
        user.id,
        UserUpdate(
            email="  New@Example.COM  ",
            password="newpassword123",
            full_name="Updated User",
        ),
    )

    assert result is reloaded
    updates = user_repository.update.await_args.args[1]
    assert updates["email"] == "new@example.com"
    assert updates["normalized_email"] == "new@example.com"
    assert updates["password_hash"].startswith("pbkdf2_sha256$")
    assert "password" not in updates
    session.commit.assert_awaited_once()


async def test_update_user_raises_conflict_for_other_users_email() -> None:
    service, session, user_repository, organization_repository = build_service()
    organization = build_organization()
    user = build_user(organization_id=organization.id)
    conflicting_user = build_user(organization_id=organization.id)
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_id_and_organization.return_value = user
    user_repository.get_by_email.return_value = conflicting_user

    with pytest.raises(ConflictError, match="User email already exists"):
        await service.update_user(
            organization.id,
            user.id,
            UserUpdate(email="other@example.com"),
        )

    user_repository.update.assert_not_called()
    session.commit.assert_not_awaited()


async def test_deactivate_user_returns_existing_when_already_inactive() -> None:
    service, session, user_repository, organization_repository = build_service()
    organization = build_organization()
    user = build_user(organization_id=organization.id, is_active=False)
    organization_repository.get_by_id.return_value = organization
    user_repository.get_by_id_and_organization.return_value = user

    result = await service.deactivate_user(organization.id, user.id)

    assert result is user
    user_repository.update.assert_not_called()
    session.commit.assert_not_awaited()


async def test_get_active_organization_raises_conflict_when_inactive() -> None:
    service, _, _, organization_repository = build_service()
    organization = build_organization(is_active=False)
    organization_repository.get_by_id.return_value = organization

    with pytest.raises(ConflictError, match="Organization is inactive"):
        await service._get_active_organization(organization.id)


async def test_validate_owner_transition_skips_non_owner_users() -> None:
    service, _, user_repository, _ = build_service()
    user = build_user(role=UserRole.AGENT)

    await service._validate_owner_state_transition(uuid4(), user, {"is_active": False})

    user_repository.count_active_owners.assert_not_called()


async def test_validate_owner_transition_raises_for_last_active_owner_deactivation(
) -> None:
    service, _, user_repository, _ = build_service()
    organization_id = uuid4()
    owner = build_user(role=UserRole.OWNER)
    user_repository.count_active_owners.return_value = 1

    with pytest.raises(
        ConflictError,
        match="Last active owner cannot be deactivated or demoted",
    ):
        await service._validate_owner_state_transition(
            organization_id,
            owner,
            {"is_active": False},
        )

    user_repository.count_active_owners.assert_awaited_once_with(organization_id)


async def test_validate_owner_transition_allows_multiple_active_owners() -> None:
    service, _, user_repository, _ = build_service()
    owner = build_user(role=UserRole.OWNER)
    user_repository.count_active_owners.return_value = 2

    await service._validate_owner_state_transition(
        uuid4(),
        owner,
        {"role": UserRole.ADMIN},
    )


def test_normalize_email_and_hash_password_helpers() -> None:
    service, _, _, _ = build_service()

    assert service._normalize_email("  User@Example.COM  ") == "user@example.com"
    password_hash = service._hash_password("strongpass123")
    assert password_hash.startswith("pbkdf2_sha256$")
    assert password_hash != "strongpass123"
