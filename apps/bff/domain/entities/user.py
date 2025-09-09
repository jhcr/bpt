from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class User:
    """BFF User entity - aggregated from multiple services"""
    
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_profile_and_settings(
        cls,
        profile_data: Dict[str, Any],
        settings_data: Optional[Dict[str, Any]] = None
    ) -> "User":
        """Create User from UserProfiles and UserSettings data"""
        
        # Map created_at/updated_at if they're strings
        created_at = None
        updated_at = None
        
        if profile_data.get("created_at"):
            if isinstance(profile_data["created_at"], str):
                created_at = datetime.fromisoformat(profile_data["created_at"].replace("Z", "+00:00"))
            else:
                created_at = profile_data["created_at"]
        
        if profile_data.get("updated_at"):
            if isinstance(profile_data["updated_at"], str):
                updated_at = datetime.fromisoformat(profile_data["updated_at"].replace("Z", "+00:00"))
            else:
                updated_at = profile_data["updated_at"]
        
        return cls(
            id=profile_data["id"],
            email=profile_data["email"],
            display_name=profile_data.get("display_name"),
            avatar_url=profile_data.get("avatar_url"),
            is_active=profile_data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at,
            settings=settings_data.get("data") if settings_data else None
        )


@dataclass
class UserSettings:
    """User settings entity"""
    
    user_id: str
    category: str
    data: Dict[str, Any]
    version: int
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        """Create UserSettings from dictionary"""
        updated_at = None
        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            else:
                updated_at = data["updated_at"]
        
        return cls(
            user_id=data["user_id"],
            category=data["category"],
            data=data["data"],
            version=data["version"],
            updated_at=updated_at
        )