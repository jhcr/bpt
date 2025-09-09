from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class UserSettingsPort(ABC):
    """Port for UserSettings service operations"""
    
    @abstractmethod
    async def get_settings(self, user_id: str, category: str) -> Optional[Dict[str, Any]]:
        """Get user settings for a specific category"""
        pass
    
    @abstractmethod
    async def get_all_settings(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all settings for a user"""
        pass
    
    @abstractmethod
    async def update_settings(
        self,
        user_id: str,
        category: str,
        data: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
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