from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class UserProfilesPort(ABC):
    """Port for UserProfiles service operations"""
    
    @abstractmethod
    async def get_user_by_sub(self, cognito_sub: str) -> Optional[Dict[str, Any]]:
        """Get user profile by Cognito subject"""
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by internal ID"""
        pass
    
    @abstractmethod
    async def create_user(
        self,
        cognito_sub: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new user profile"""
        pass
    
    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user profile"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user profile"""
        pass