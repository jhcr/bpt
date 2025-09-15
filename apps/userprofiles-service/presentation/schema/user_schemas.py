import os
import sys
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from domain.entities.user import User


class CreateUserRequest(BaseModel):
    """Request schema for creating a user"""

    cognito_sub: str = Field(..., description="Cognito subject identifier")
    email: EmailStr = Field(..., description="User email address")
    display_name: str | None = Field(None, description="Display name")
    avatar_url: str | None = Field(None, description="Avatar URL")
    phone: str | None = Field(None, description="Phone number")


class UpdateUserRequest(BaseModel):
    """Request schema for updating a user"""

    email: EmailStr | None = Field(None, description="User email address")
    display_name: str | None = Field(None, description="Display name")
    avatar_url: str | None = Field(None, description="Avatar URL")
    phone: str | None = Field(None, description="Phone number")
    is_active: bool | None = Field(None, description="User active status")


class UserResponse(BaseModel):
    """Response schema for user data"""

    id: str
    cognito_sub: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        """Convert User entity to response schema"""
        return cls(
            id=user.id,
            cognito_sub=user.cognito_sub,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserListResponse(BaseModel):
    """Response schema for user list"""

    users: list[UserResponse]
    total: int
    limit: int
    offset: int
