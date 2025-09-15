from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class User:
    """BFF User entity - aggregated from multiple services"""

    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    settings: dict[str, Any] | None = None

    @classmethod
    def from_profile_and_settings(
        cls, profile_data: dict[str, Any], settings_data: dict[str, Any] | None = None
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
            settings=settings_data.get("data") if settings_data else None,
        )


@dataclass
class UserSettings:
    """User settings entity"""

    user_id: str
    category: str
    data: dict[str, Any]
    version: int
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSettings":
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
            updated_at=updated_at,
        )


@dataclass
class UserSettingsCollection:
    """Collection of user settings grouped by category"""

    user_id: str
    settings: dict[str, dict[str, Any]]  # category -> {data, version, updated_at}

    @classmethod
    def from_settings_list(cls, user_id: str, settings_list: list[dict[str, Any]]) -> "UserSettingsCollection":
        """Create UserSettingsCollection from list of settings"""
        settings_by_category = {}
        for setting in settings_list:
            updated_at = setting.get("updated_at")
            if updated_at and isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

            settings_by_category[setting["category"]] = {
                "data": setting["data"],
                "version": setting["version"],
                "updated_at": updated_at,
            }

        return cls(user_id=user_id, settings=settings_by_category)
