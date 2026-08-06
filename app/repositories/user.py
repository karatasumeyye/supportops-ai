from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        full_name: str,
        email: str,
        normalized_email: str,
        password_hash: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        user = User(
            organization_id=organization_id,
            full_name=full_name,
            email=email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_and_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> User | None:
        query = select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, normalized_email: str) -> User | None:
        query = select(User).where(User.normalized_email == normalized_email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_normalized_email(
        self,
        normalized_email: str,
    ) -> User | None:
        return await self.get_by_email(normalized_email)

    async def exists_by_email(self, normalized_email: str) -> bool:
        query = select(User.id).where(User.normalized_email == normalized_email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def exists_by_normalized_email(self, normalized_email: str) -> bool:
        return await self.exists_by_email(normalized_email)

    async def list_by_organization(
        self,
        organization_id: UUID,
    ) -> list[User]:
        query = (
            select(User)
            .where(User.organization_id == organization_id)
            .order_by(User.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        user: User,
        updates: Mapping[str, object],
    ) -> User:
        for field, value in updates.items():
            setattr(user, field, value)

        await self.session.flush()
        return user

    async def count_active_owners(self, organization_id: UUID) -> int:
        query = select(func.count(User.id)).where(
            User.organization_id == organization_id,
            User.role == UserRole.OWNER,
            User.is_active.is_(True),
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())
