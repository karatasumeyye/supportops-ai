from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact


class ContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        full_name: str,
        email: str | None,
        normalized_email: str | None,
        phone: str | None,
        is_active: bool = True,
    ) -> Contact:
        contact = Contact(
            organization_id=organization_id,
            full_name=full_name,
            email=email,
            normalized_email=normalized_email,
            phone=phone,
            is_active=is_active,
        )

        self.session.add(contact)
        await self.session.flush()
        return contact

    async def get_by_id_and_organization(
        self,
        contact_id: UUID,
        organization_id: UUID,
    ) -> Contact | None:
        query = select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_normalized_email_and_organization(
        self,
        organization_id: UUID,
        normalized_email: str,
    ) -> Contact | None:
        query = select(Contact).where(
            Contact.organization_id == organization_id,
            Contact.normalized_email == normalized_email,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> list[Contact]:
        query = self._build_filtered_query(
            organization_id=organization_id,
            is_active=is_active,
            search=search,
        ).order_by(Contact.created_at.desc(), Contact.id.desc())
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_organization(
        self,
        organization_id: UUID,
        *,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        query = (
            select(func.count(Contact.id))
            .select_from(Contact)
            .where(Contact.organization_id == organization_id)
        )
        query = self._apply_filters(
            query,
            is_active=is_active,
            search=search,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def update(
        self,
        contact: Contact,
        updates: dict[str, object],
    ) -> Contact:
        for field, value in updates.items():
            setattr(contact, field, value)

        await self.session.flush()
        return contact

    def _build_filtered_query(
        self,
        *,
        organization_id: UUID,
        is_active: bool | None,
        search: str | None,
    ) -> Any:
        query = select(Contact).where(Contact.organization_id == organization_id)
        return self._apply_filters(
            query,
            is_active=is_active,
            search=search,
        )

    def _apply_filters(
        self,
        query: Any,
        *,
        is_active: bool | None,
        search: str | None,
    ) -> Any:
        if is_active is not None:
            query = query.where(Contact.is_active.is_(is_active))

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Contact.full_name.ilike(search_term),
                    Contact.email.ilike(search_term),
                    Contact.phone.ilike(search_term),
                )
            )

        return query
