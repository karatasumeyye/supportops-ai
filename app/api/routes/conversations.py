from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.models.enums import SupportRequestPriority, SupportRequestStatus
from app.models.support_request import SupportRequest
from app.schemas.support_request import (
    SupportRequestAssign,
    SupportRequestCreate,
    SupportRequestCreateResponse,
    SupportRequestListResponse,
    SupportRequestResponse,
    SupportRequestStatusUpdate,
    SupportRequestUpdate,
)
from app.services.support_request import SupportRequestService

router = APIRouter(
    prefix="/organizations/{organization_id}/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=SupportRequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    organization_id: UUID,
    conversation_data: SupportRequestCreate,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequestCreateResponse:
    service = SupportRequestService(session)

    return await service.create_support_request(
        organization_id,
        conversation_data,
    )


@router.get(
    "",
    response_model=SupportRequestListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conversations(
    organization_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: SupportRequestStatus | None = Query(default=None, alias="status"),
    priority: SupportRequestPriority | None = None,
    assigned_user_id: UUID | None = None,
    contact_id: UUID | None = None,
    search: str | None = None,
    unassigned: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequestListResponse:
    if unassigned is True and assigned_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=("assigned_user_id cannot be combined with unassigned=true."),
        )

    service = SupportRequestService(session)

    return await service.list_support_requests(
        organization_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        priority=priority,
        assigned_user_id=assigned_user_id,
        contact_id=contact_id,
        search=search,
        unassigned=unassigned,
    )


@router.get(
    "/{conversation_id}",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def get_conversation(
    organization_id: UUID,
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequest:
    service = SupportRequestService(session)

    return await service.get_support_request(
        organization_id,
        conversation_id,
    )


@router.patch(
    "/{conversation_id}",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def update_conversation(
    organization_id: UUID,
    conversation_id: UUID,
    conversation_data: SupportRequestUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequest:
    service = SupportRequestService(session)

    return await service.update_support_request(
        organization_id,
        conversation_id,
        conversation_data,
    )


@router.post(
    "/{conversation_id}/assign",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_conversation(
    organization_id: UUID,
    conversation_id: UUID,
    assignment_data: SupportRequestAssign,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequest:
    service = SupportRequestService(session)

    return await service.assign_support_request(
        organization_id,
        conversation_id,
        assignment_data.assigned_user_id,
    )


@router.post(
    "/{conversation_id}/unassign",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def unassign_conversation(
    organization_id: UUID,
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequest:
    service = SupportRequestService(session)

    return await service.unassign_support_request(
        organization_id,
        conversation_id,
    )


@router.post(
    "/{conversation_id}/transition",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_conversation(
    organization_id: UUID,
    conversation_id: UUID,
    transition_data: SupportRequestStatusUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> SupportRequest:
    service = SupportRequestService(session)

    return await service.transition_support_request(
        organization_id,
        conversation_id,
        transition_data.status,
    )
