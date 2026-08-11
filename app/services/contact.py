from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact
from app.models.organization import Organization
from app.repositories.contact import ContactRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.contact import ContactCreate, ContactListResponse, ContactUpdate


class ContactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contact_repository = ContactRepository(session)
        self.organization_repository = OrganizationRepository(session)

    async def create_contact(
        self,
        organization_id: UUID,
        contact_data: ContactCreate,
    ) -> Contact:
        organization = await self._get_active_organization(organization_id)
        normalized_email = self._normalize_email(contact_data.email)

        if normalized_email is not None:
            existing_contact = (
                await self.contact_repository.get_by_normalized_email_and_organization(
                    organization.id,
                    normalized_email,
                )
            )
            if existing_contact is not None:
                raise ConflictError(f"Contact email already exists: {normalized_email}")

        contact = await self.contact_repository.create(
            organization_id=organization.id,
            full_name=contact_data.full_name,
            email=normalized_email,
            normalized_email=normalized_email,
            phone=contact_data.phone,
        )

        await self.session.commit()
        return contact

    async def get_contact(
        self,
        organization_id: UUID,
        contact_id: UUID,
    ) -> Contact:
        await self._get_organization(organization_id)

        contact = await self.contact_repository.get_by_id_and_organization(
            contact_id,
            organization_id,
        )
        if contact is None:
            raise NotFoundError(f"Contact not found: {contact_id}")

        return contact

    async def list_organization_contacts(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> ContactListResponse:
        await self._get_organization(organization_id)

        normalized_search = self._normalize_search(search)
        items = await self.contact_repository.list_by_organization(
            organization_id,
            limit=limit,
            offset=offset,
            is_active=is_active,
            search=normalized_search,
        )
        total = await self.contact_repository.count_by_organization(
            organization_id,
            is_active=is_active,
            search=normalized_search,
        )

        return ContactListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_contact(
        self,
        organization_id: UUID,
        contact_id: UUID,
        contact_data: ContactUpdate,
    ) -> Contact:
        organization = await self._get_active_organization(organization_id)
        contact = await self.get_contact(organization.id, contact_id)

        updates = contact_data.model_dump(exclude_unset=True)

        if "email" in updates:
            normalized_email = self._normalize_email(updates["email"])
            if normalized_email is not None:
                existing_contact = await (
                    self.contact_repository.get_by_normalized_email_and_organization(
                        organization.id,
                        normalized_email,
                    )
                )
                if existing_contact is not None and existing_contact.id != contact.id:
                    raise ConflictError(
                        f"Contact email already exists: {normalized_email}"
                    )

            updates["email"] = normalized_email
            updates["normalized_email"] = normalized_email

        updated_contact = await self.contact_repository.update(contact, updates)
        await self.session.commit()
        reloaded_contact = await self.contact_repository.get_by_id_and_organization(
            updated_contact.id,
            organization.id,
        )
        assert reloaded_contact is not None
        return reloaded_contact

    async def deactivate_contact(
        self,
        organization_id: UUID,
        contact_id: UUID,
    ) -> Contact:
        await self._get_active_organization(organization_id)
        contact = await self.get_contact(organization_id, contact_id)

        if not contact.is_active:
            return contact

        updated_contact = await self.contact_repository.update(
            contact,
            {"is_active": False},
        )
        await self.session.commit()
        reloaded_contact = await self.contact_repository.get_by_id_and_organization(
            updated_contact.id,
            organization_id,
        )
        assert reloaded_contact is not None
        return reloaded_contact

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

    def _normalize_email(self, email: object) -> str | None:
        if email is None:
            return None

        return str(email).strip().lower()

    def _normalize_search(self, search: str | None) -> str | None:
        if search is None:
            return None

        normalized = search.strip()
        return normalized or None
