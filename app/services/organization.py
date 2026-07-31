from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:

    # service and repository use same async session, so that they can share the same transaction context. This allows for better control over transactions and ensures that changes made in the service layer are properly persisted in the database.
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = OrganizationRepository(session)

    async def create(self,organization_data: OrganizationCreate,) -> Organization:

        existing_organization = await self.repository.get_by_slug(
            organization_data.slug,
        )

        if existing_organization is not None:
            raise ConflictError(
                f"Organization slug already exists: {organization_data.slug}"
            )

        organization = await self.repository.create(
            organization_data,
        )

        await self.session.commit()  # Commit the transaction to persist the changes to the database
        await self.session.refresh(organization)

        return organization

    async def get_by_id(self,organization_id: UUID,) -> Organization:

        organization = await self.repository.get_by_id(
            organization_id,
        )

        if organization is None:
            raise NotFoundError(
                f"Organization not found: {organization_id}"
            )

        return organization

    async def list_all(self) -> list[Organization]:

        return await self.repository.list_all()

    async def update(self,organization_id: UUID,organization_data: OrganizationUpdate,) -> Organization:

        organization = await self.get_by_id(
            organization_id,
        )

        if (organization_data.slug is not None and organization_data.slug != organization.slug):

            organization_with_same_slug = (
                await self.repository.get_by_slug(organization_data.slug,)
            )

            if organization_with_same_slug is not None:
                raise ConflictError(
                    f"Organization slug already exists: "
                    f"{organization_data.slug}"
                )

        updated_organization = await self.repository.update(
            organization,
            organization_data,
        )

        await self.session.commit()
        await self.session.refresh(updated_organization)

        return updated_organization