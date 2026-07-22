import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.user import UserRole
from app.schemas.base import APIModel


class UserBase(APIModel):
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )
    
    email: EmailStr


class UserCreate(UserBase):
    organization_id: uuid.UUID
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    role: UserRole

class UserUpdate(APIModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    role: UserRole | None = None

    is_active: bool | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
