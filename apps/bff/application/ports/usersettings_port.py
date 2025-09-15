from abc import ABC, abstractmethod
from typing import Any


class UserSettingsPort(ABC):
    """Port for UserSettings service operations"""

    @abstractmethod
    async def get_settings(self, user_id: str, category: str) -> dict[str, Any] | None:
        """Get user settings for a specific category"""
        pass

    @abstractmethod
    async def get_all_settings(self, user_id: str) -> list[dict[str, Any]]:
        """Get all settings for a user"""
        pass

    @abstractmethod
    async def update_settings(
        self,
        user_id: str,
        category: str,
        data: dict[str, Any],
        expected_version: int | None = None,
    ) -> dict[str, Any] | None:
        """Update user settings with optimistic concurrency control"""
        pass

    @abstractmethod
    async def delete_settings(self, user_id: str, category: str) -> bool:
        """Delete user settings for a category"""
        pass

    @abstractmethod
    async def delete_all_settings(self, user_id: str) -> int:
        """Delete all settings for a user, return count deleted"""
        pass
