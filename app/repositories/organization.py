from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate

class OrganizationRepository:
    # The repository does not create its own session; it uses the session provided from the outside.
    def __init__(self,session: AsyncSession)-> None:
        self.session = session


    async def create(self, organization_data: OrganizationCreate,)-> Organization:
        organization = Organization(
            **organization_data.model_dump(), # Unpack the fields from the OrganizationCreate schema to create a new Organization instance
        )

        self.session.add(organization) # Add the new organization to the session
        await self.session.flush() # Flush the session to persist the changes to the database
        return organization

    async def get_by_id(self, organization_id: UUID) -> Organization | None:

        query = select(Organization).where(Organization.id == organization_id)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()  # Return the organization if found, otherwise return None

    async def get_by_slug(self,slug:str)-> Organization | None:

        query = select(Organization).where(Organization.slug == slug)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()  

    async def list_all(self) -> list[Organization]:
        query = select(Organization).order_by(Organization.created_at.desc())  # Order by creation date, most recent first
        result = await self.session.execute(query)

        return list(result.scalars().all())  # Return a list of all organizations

    async def update(self, organization: Organization, organization_data: OrganizationUpdate) -> Organization:
        updated_data = organization_data.model_dump(exclude_unset=True)  # Get only the fields that were set in the update request
        for field, value in updated_data.items():
            setattr(organization, field, value)  # Update the organization with the new values

        await self.session.flush()  # Flush the session to persist the changes to the database

        return organization