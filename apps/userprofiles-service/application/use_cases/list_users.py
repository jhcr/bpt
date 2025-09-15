import structlog

from application.ports.user_repository import UserRepository
from domain.entities.user import User

logger = structlog.get_logger(__name__)


class ListUsers:
    """Use case for listing user profiles"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List active users with pagination"""
        logger.info("Listing users", limit=limit, offset=offset)

        if limit > 1000:
            limit = 1000  # Enforce maximum limit

        users = await self.user_repository.list_active_users(limit=limit, offset=offset)
        logger.info("Users retrieved", count=len(users), limit=limit, offset=offset)

        return users

    async def count(self) -> int:
        """Count active users"""
        logger.info("Counting active users")
        count = await self.user_repository.count_active_users()
        logger.info("Active user count", count=count)
        return count
