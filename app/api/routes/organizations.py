from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    organization_data: OrganizationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    service = OrganizationService(session)

    return await service.create(organization_data)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_organizations(
    session: AsyncSession = Depends(get_db_session),
) -> list[Organization]:
    service = OrganizationService(session)

    return await service.list_all()


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_organization(
    organization_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    service = OrganizationService(session)

    return await service.get_by_id(organization_id)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_organization(
    organization_id: UUID,
    organization_data: OrganizationUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    service = OrganizationService(session)

    return await service.update(
        organization_id,
        organization_data,
    )