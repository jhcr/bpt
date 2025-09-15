# Assumptions:
# - Repository interface for UserSettings persistence
# - Support for OCC operations
# - Abstract base class for dependency inversion

from abc import ABC, abstractmethod
from typing import List

from domain.entities.user_setting import UserSetting


class UserSettingsRepository(ABC):
    """Abstract repository for user settings"""

    @abstractmethod
    async def get_setting(self, user_id: str, category: str) -> UserSetting | None:
        """Get user setting by user_id and category"""
        pass

    @abstractmethod
    async def get_all_settings(self, user_id: str) -> List[UserSetting]:
        """Get all settings for a user"""
        pass

    @abstractmethod
    async def save_setting(self, setting: UserSetting, expected_version: int | None = None) -> UserSetting:
        """
        Save user setting with optional optimistic concurrency control

        Args:
            setting: UserSetting to save
            expected_version: Expected version for OCC, None for new setting

        Returns:
            Saved setting with updated version

        Raises:
            VersionConflictError: If expected_version doesn't match current version
        """
        pass

    @abstractmethod
    async def delete_setting(self, user_id: str, category: str) -> bool:
        """
        Delete user setting

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_all_settings(self, user_id: str) -> int:
        """
        Delete all settings for a user

        Returns:
            Number of settings deleted
        """
        pass
