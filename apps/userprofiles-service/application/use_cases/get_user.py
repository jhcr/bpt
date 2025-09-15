import structlog

from application.ports.user_repository import UserRepository
from domain.entities.user import User

logger = structlog.get_logger(__name__)


class GetUser:
    """Use case for retrieving user profiles"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def by_id(self, user_id: str) -> User | None:
        """Get user by ID"""
        logger.info("Getting user by ID", user_id=user_id)
        user = await self.user_repository.get_by_id(user_id)
        if user:
            logger.info("User found", user_id=user_id, email=user.email)
        else:
            logger.info("User not found", user_id=user_id)
        return user

    async def by_cognito_sub(self, cognito_sub: str) -> User | None:
        """Get user by Cognito subject"""
        logger.info("Getting user by Cognito sub", cognito_sub=cognito_sub)
        user = await self.user_repository.get_by_cognito_sub(cognito_sub)
        if user:
            logger.info("User found", cognito_sub=cognito_sub, user_id=user.id, email=user.email)
        else:
            logger.info("User not found", cognito_sub=cognito_sub)
        return user

    async def by_email(self, email: str) -> User | None:
        """Get user by email"""
        logger.info("Getting user by email", email=email)
        user = await self.user_repository.get_by_email(email)
        if user:
            logger.info("User found", email=email, user_id=user.id)
        else:
            logger.info("User not found", email=email)
        return user
