from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class UserResponse(BaseModel):
    """User profile response"""
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    settings: Dict[str, Any] = {}


class UserSettingsResponse(BaseModel):
    """User settings response"""
    user_id: str
    category: Optional[str] = None  # Present for single category, None for all
    data: Optional[Dict[str, Any]] = None  # Present for single category
    version: Optional[int] = None  # Present for single category
    updated_at: Optional[str] = None  # Present for single category
    settings: Optional[Dict[str, Dict[str, Any]]] = None  # Present for all categories


class UpdateUserSettingsRequest(BaseModel):
    """Request to update user settings"""
    data: Dict[str, Any]
    expected_version: Optional[int] = None