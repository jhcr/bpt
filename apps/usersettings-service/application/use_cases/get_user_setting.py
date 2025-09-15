# Assumptions:
# - Use case for getting user settings
# - Returns None if not found
# - Clean architecture principles


import structlog

from domain.entities.user_setting import UserSetting
from application.ports.user_settings_repository import UserSettingsRepository

logger = structlog.get_logger(__name__)


class GetUserSetting:
    """Use case for getting user setting"""

    def __init__(self, repository: UserSettingsRepository):
        self.repository = repository

    async def execute(self, user_id: str, category: str) -> UserSetting | None:
        """
        Get user setting by user_id and category

        Args:
            user_id: User identifier
            category: Setting category

        Returns:
            UserSetting if found, None otherwise
        """
        try:
            logger.debug("Getting user setting", user_id=user_id, category=category)

            setting = await self.repository.get_setting(user_id, category)

            if setting:
                logger.debug("User setting retrieved", user_id=user_id, category=category, version=setting.version)
            else:
                logger.debug("User setting not found", user_id=user_id, category=category)

            return setting

        except Exception as e:
            logger.error("Failed to get user setting", user_id=user_id, category=category, error=str(e))
            raise
