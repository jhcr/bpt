# Assumptions:
# - Use case for deleting user settings
# - Returns boolean for success/failure
# - Clean architecture principles

import structlog

from application.ports.user_settings_repository import UserSettingsRepository

logger = structlog.get_logger(__name__)


class DeleteUserSetting:
    """Use case for deleting user setting"""

    def __init__(self, repository: UserSettingsRepository):
        self.repository = repository

    async def execute(self, user_id: str, category: str) -> bool:
        """
        Delete user setting

        Args:
            user_id: User identifier
            category: Setting category

        Returns:
            True if deleted, False if not found
        """
        try:
            logger.info("Deleting user setting", user_id=user_id, category=category)

            deleted = await self.repository.delete_setting(user_id, category)

            if deleted:
                logger.info("User setting deleted", user_id=user_id, category=category)
            else:
                logger.info("User setting not found for deletion", user_id=user_id, category=category)

            return deleted

        except Exception as e:
            logger.error("Failed to delete user setting", user_id=user_id, category=category, error=str(e))
            raise


class DeleteAllUserSettings:
    """Use case for deleting all user settings"""

    def __init__(self, repository: UserSettingsRepository):
        self.repository = repository

    async def execute(self, user_id: str) -> int:
        """
        Delete all settings for a user

        Args:
            user_id: User identifier

        Returns:
            Number of settings deleted
        """
        try:
            logger.info("Deleting all user settings", user_id=user_id)

            count = await self.repository.delete_all_settings(user_id)

            logger.info("All user settings deleted", user_id=user_id, count=count)

            return count

        except Exception as e:
            logger.error("Failed to delete all user settings", user_id=user_id, error=str(e))
            raise
