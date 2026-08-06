import hashlib
import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 100_000
PBKDF2_SALT_BYTES = 16


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.organization_repository = OrganizationRepository(session)

    async def create_user(
        self,
        organization_id: UUID,
        user_data: UserCreate,
    ) -> User:
        organization = await self._get_active_organization(organization_id)
        normalized_email = self._normalize_email(user_data.email)

        existing_user = await self.user_repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise ConflictError(f"User email already exists: {normalized_email}")

        password_hash = self._hash_password(user_data.password)

        user = await self.user_repository.create(
            organization_id=organization.id,
            full_name=user_data.full_name,
            email=normalized_email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            role=user_data.role,
        )

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> User:
        await self._get_organization(organization_id)

        user = await self.user_repository.get_by_id_and_organization(
            user_id,
            organization_id,
        )
        if user is None:
            raise NotFoundError(f"User not found: {user_id}")

        return user

    async def list_organization_users(
        self,
        organization_id: UUID,
    ) -> list[User]:
        await self._get_organization(organization_id)
        return await self.user_repository.list_by_organization(organization_id)

    async def update_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        user_data: UserUpdate,
    ) -> User:
        organization = await self._get_active_organization(organization_id)
        user = await self.get_user(organization.id, user_id)

        updates = user_data.model_dump(exclude_unset=True)

        if "email" in updates:
            normalized_email = self._normalize_email(updates["email"])
            existing_user = await self.user_repository.get_by_email(normalized_email)
            if existing_user is not None and existing_user.id != user.id:
                raise ConflictError(f"User email already exists: {normalized_email}")

            updates["email"] = normalized_email
            updates["normalized_email"] = normalized_email

        if "password" in updates:
            updates["password_hash"] = self._hash_password(updates["password"])
            del updates["password"]

        await self._validate_owner_state_transition(
            organization.id,
            user,
            updates,
        )

        updated_user = await self.user_repository.update(user, updates)
        await self.session.commit()
        await self.session.refresh(updated_user)
        return updated_user

    async def deactivate_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> User:
        user = await self.get_user(organization_id, user_id)

        if not user.is_active:
            return user

        await self._validate_owner_state_transition(
            organization_id,
            user,
            {"is_active": False},
        )

        updated_user = await self.user_repository.update(
            user,
            {"is_active": False},
        )
        await self.session.commit()
        await self.session.refresh(updated_user)
        return updated_user

    async def _get_organization(self, organization_id: UUID) -> Organization:
        organization = await self.organization_repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization not found: {organization_id}")

        return organization

    async def _get_active_organization(
        self,
        organization_id: UUID,
    ) -> Organization:
        organization = await self._get_organization(organization_id)
        if not organization.is_active:
            raise ConflictError(f"Organization is inactive: {organization_id}")

        return organization

    async def _validate_owner_state_transition(
        self,
        organization_id: UUID,
        user: User,
        updates: dict[str, object],
    ) -> None:
        is_owner = user.role == UserRole.OWNER
        role_change = updates.get("role")
        is_active_change = updates.get("is_active")

        if not is_owner:
            return

        deactivating_owner = is_active_change is False
        demoting_owner = role_change is not None and role_change != UserRole.OWNER

        if not deactivating_owner and not demoting_owner:
            return

        active_owner_count = await self.user_repository.count_active_owners(
            organization_id
        )
        if active_owner_count <= 1:
            raise ConflictError("Last active owner cannot be deactivated or demoted.")

    def _normalize_email(self, email: object) -> str:
        return str(email).strip().lower()

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
        password_hash = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return (
            f"pbkdf2_{PBKDF2_ALGORITHM}$"
            f"{PBKDF2_ITERATIONS}$"
            f"{salt.hex()}$"
            f"{password_hash.hex()}"
        )
