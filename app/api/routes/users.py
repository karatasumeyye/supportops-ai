from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter(
    prefix="/organizations/{organization_id}/users",
    tags=["Users"],
)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    organization_id: UUID,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    service = UserService(session)

    return await service.create_user(organization_id, user_data)


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    organization_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[User]:
    service = UserService(session)

    return await service.list_organization_users(organization_id)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(
    organization_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    service = UserService(session)

    return await service.get_user(organization_id, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user(
    organization_id: UUID,
    user_id: UUID,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    service = UserService(session)

    return await service.update_user(
        organization_id,
        user_id,
        user_data,
    )


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def deactivate_user(
    organization_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    service = UserService(session)

    return await service.deactivate_user(organization_id, user_id)
