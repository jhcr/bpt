import structlog

from application.ports.user_repository import UserRepository
from domain.entities.user import User

logger = structlog.get_logger(__name__)


class UpdateUser:
    """Use case for updating user profiles"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(
        self,
        user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update user profile"""
        logger.info("Updating user profile", user_id=user_id)

        # Get existing user
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            logger.error("User not found for update", user_id=user_id)
            raise ValueError(f"User {user_id} not found")

        # Check if email is being changed and already taken
        if email and email != existing_user.email:
            existing_email = await self.user_repository.get_by_email(email)
            if existing_email:
                logger.warning("Email already taken", email=email, existing_user_id=existing_email.id)
                raise ValueError(f"Email {email} is already registered")

        # Update user
        updated_user = existing_user.update(
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            phone=phone,
            is_active=is_active,
        )

        # Persist updated user
        persisted_user = await self.user_repository.update(updated_user)
        logger.info("User profile updated", user_id=persisted_user.id, email=persisted_user.email)

        return persisted_user
