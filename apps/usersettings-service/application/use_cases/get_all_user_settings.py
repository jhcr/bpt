# Assumptions:
# - Use case for getting all user settings
# - Returns empty list if no settings found
# - Clean architecture principles

from typing import List

import structlog

from domain.entities.user_setting import UserSetting
from application.ports.user_settings_repository import UserSettingsRepository

logger = structlog.get_logger(__name__)


class GetAllUserSettings:
    """Use case for getting all user settings"""

    def __init__(self, repository: UserSettingsRepository):
        self.repository = repository

    async def execute(self, user_id: str) -> List[UserSetting]:
        """
        Get all settings for a user

        Args:
            user_id: User identifier

        Returns:
            List of UserSetting objects (empty if none found)
        """
        try:
            logger.debug("Getting all user settings", user_id=user_id)

            settings = await self.repository.get_all_settings(user_id)

            logger.debug("User settings retrieved", user_id=user_id, count=len(settings))

            return settings

        except Exception as e:
            logger.error("Failed to get all user settings", user_id=user_id, error=str(e))
            raise
