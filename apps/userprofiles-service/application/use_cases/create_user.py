import structlog

from application.ports.user_repository import UserRepository
from domain.entities.user import User

logger = structlog.get_logger(__name__)


class CreateUser:
    """Use case for creating user profiles"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(
        self,
        cognito_sub: str,
        email: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
    ) -> User:
        """Create a new user profile"""
        logger.info("Creating user profile", email=email, cognito_sub=cognito_sub)

        # Check if user already exists
        existing_user = await self.user_repository.get_by_cognito_sub(cognito_sub)
        if existing_user:
            logger.warning("User already exists", cognito_sub=cognito_sub, user_id=existing_user.id)
            raise ValueError(f"User with cognito_sub {cognito_sub} already exists")

        # Check if email is already taken
        existing_email = await self.user_repository.get_by_email(email)
        if existing_email:
            logger.warning("Email already taken", email=email, user_id=existing_email.id)
            raise ValueError(f"Email {email} is already registered")

        # Create new user
        user = User.create(
            cognito_sub=cognito_sub,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            phone=phone,
        )

        # Persist user
        created_user = await self.user_repository.create(user)
        logger.info("User profile created", user_id=created_user.id, email=created_user.email)

        return created_user
