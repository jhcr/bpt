from typing import Any

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User profile response"""

    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None
    settings: dict[str, Any] = {}


class UserSettingsResponse(BaseModel):
    """User settings response"""

    user_id: str
    category: str | None = None  # Present for single category, None for all
    data: dict[str, Any] | None = None  # Present for single category
    version: int | None = None  # Present for single category
    updated_at: str | None = None  # Present for single category
    settings: dict[str, dict[str, Any]] | None = None  # Present for all categories


class UpdateUserSettingsRequest(BaseModel):
    """Request to update user settings"""

    data: dict[str, Any]
    expected_version: int | None = None
