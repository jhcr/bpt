"""Port for user persistence operations"""

from abc import ABC, abstractmethod

from domain.entities.user import User


class UserRepository(ABC):
    """Port for user persistence operations"""

    @abstractmethod
    async def save_user(self, user: User) -> None:
        """Save or update a user"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by internal ID"""
        pass

    @abstractmethod
    async def get_user_by_provider_sub(self, provider_sub: str) -> User | None:
        """Get user by provider subject identifier"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID"""
        pass

    @abstractmethod
    async def list_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List users with pagination"""
        pass

    @abstractmethod
    async def update_user_status(self, user_id: str, status: str) -> None:
        """Update user status"""
        pass

    @abstractmethod
    async def user_exists(self, provider_sub: str) -> bool:
        """Check if user exists by provider subject"""
        pass
