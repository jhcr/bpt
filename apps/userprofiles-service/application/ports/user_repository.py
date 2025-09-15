from abc import ABC, abstractmethod

from domain.entities.user import User


class UserRepository(ABC):
    """User repository interface"""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_cognito_sub(self, cognito_sub: str) -> User | None:
        """Get user by Cognito subject"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email"""
        pass

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create new user"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user"""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user by ID"""
        pass

    @abstractmethod
    async def list_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List active users with pagination"""
        pass

    @abstractmethod
    async def count_active_users(self) -> int:
        """Count active users"""
        pass
