# Assumptions:
# - Pydantic schemas for API request/response validation
# - Support for OCC via version field
# - Clear separation of request/response models

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field


class UserSettingData(BaseModel):
    """Base schema for user setting data"""

    data: dict[str, Any] = Field(..., description="Setting data as key-value pairs")


class UpdateUserSettingRequest(UserSettingData):
    """Request schema for updating user setting"""

    expected_version: int | None = Field(None, description="Expected version for optimistic concurrency control")


class UserSettingResponse(BaseModel):
    """Response schema for user setting"""

    user_id: str = Field(..., description="User identifier")
    category: str = Field(..., description="Setting category")
    data: dict[str, Any] = Field(..., description="Setting data")
    version: int = Field(..., description="Setting version for OCC")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class UserSettingsListResponse(BaseModel):
    """Response schema for list of user settings"""

    settings: List[UserSettingResponse] = Field(..., description="List of user settings")
    count: int = Field(..., description="Total number of settings")


class DeleteUserSettingResponse(BaseModel):
    """Response schema for delete operation"""

    deleted: bool = Field(..., description="Whether setting was deleted")
    user_id: str = Field(..., description="User identifier")
    category: str = Field(..., description="Setting category")


class DeleteAllUserSettingsResponse(BaseModel):
    """Response schema for delete all operation"""

    deleted_count: int = Field(..., description="Number of settings deleted")
    user_id: str = Field(..., description="User identifier")


class ErrorResponse(BaseModel):
    """Error response schema"""

    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
