from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.schemas.request_message import (
    RequestMessageCreate,
    RequestMessageListResponse,
    RequestMessageResponse,
)
from app.services.request_message import RequestMessageService

router = APIRouter(
    prefix="/organizations/{organization_id}/conversations/{conversation_id}/messages",
    tags=["Messages"],
)


@router.post(
    "",
    response_model=RequestMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    organization_id: UUID,
    conversation_id: UUID,
    message_data: RequestMessageCreate,
    session: AsyncSession = Depends(get_db_session),
) -> RequestMessageResponse:
    service = RequestMessageService(session)
    return await service.create_message(
        organization_id,
        conversation_id,
        message_data,
    )


@router.get(
    "",
    response_model=RequestMessageListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_messages(
    organization_id: UUID,
    conversation_id: UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> RequestMessageListResponse:
    service = RequestMessageService(session)
    return await service.list_messages(
        organization_id,
        conversation_id,
        limit=limit,
        cursor=cursor,
    )
