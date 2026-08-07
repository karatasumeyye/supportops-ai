from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.models.contact import Contact
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.services.contact import ContactService

router = APIRouter(
    prefix="/organizations/{organization_id}/contacts",
    tags=["Contacts"],
)


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    organization_id: UUID,
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Contact:
    service = ContactService(session)

    return await service.create_contact(organization_id, contact_data)


@router.get(
    "",
    response_model=ContactListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_contacts(
    organization_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_active: bool | None = None,
    search: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ContactListResponse:
    service = ContactService(session)

    return await service.list_organization_contacts(
        organization_id,
        limit=limit,
        offset=offset,
        is_active=is_active,
        search=search,
    )


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
)
async def get_contact(
    organization_id: UUID,
    contact_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Contact:
    service = ContactService(session)

    return await service.get_contact(organization_id, contact_id)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
)
async def update_contact(
    organization_id: UUID,
    contact_id: UUID,
    contact_data: ContactUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Contact:
    service = ContactService(session)

    return await service.update_contact(
        organization_id,
        contact_id,
        contact_data,
    )


@router.post(
    "/{contact_id}/deactivate",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
)
async def deactivate_contact(
    organization_id: UUID,
    contact_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Contact:
    service = ContactService(session)

    return await service.deactivate_contact(organization_id, contact_id)
