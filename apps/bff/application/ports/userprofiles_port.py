from abc import ABC, abstractmethod
from typing import Any


class UserProfilesPort(ABC):
    """Port for UserProfiles service operations"""

    @abstractmethod
    async def get_user_by_sub(self, cognito_sub: str) -> dict[str, Any] | None:
        """Get user profile by Cognito subject"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user profile by internal ID"""
        pass

    @abstractmethod
    async def create_user(
        self,
        cognito_sub: str,
        email: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> dict[str, Any]:
        """Create new user profile"""
        pass

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update user profile"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user profile"""
        pass
