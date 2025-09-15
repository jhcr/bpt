from typing import Any

import structlog

from application.ports.usersettings_port import UserSettingsPort
from domain.entities.user import UserSettings, UserSettingsCollection

logger = structlog.get_logger(__name__)


class UpdateUserSettings:
    """Use case for updating user settings"""

    def __init__(self, usersettings_port: UserSettingsPort):
        self.usersettings_port = usersettings_port

    async def execute(
        self,
        user_id: str,
        category: str,
        settings_data: dict[str, Any],
        expected_version: int | None = None,
    ) -> UserSettings:
        """
        Update user settings

        Args:
            user_id: User ID to update settings for
            category: Settings category
            settings_data: Settings data to update
            expected_version: Expected version for optimistic locking

        Returns:
            Updated UserSettings domain entity
        """
        try:
            logger.info(
                "Updating user settings",
                user_id=user_id,
                category=category,
            )

            # Update settings
            result = await self.usersettings_port.update_settings(
                user_id=user_id,
                category=category,
                data=settings_data,
                expected_version=expected_version,
            )

            if not result:
                logger.warning("Settings update failed", user_id=user_id, category=category)
                raise ValueError("Failed to update settings - version conflict or user not found")

            logger.info(
                "User settings updated successfully",
                user_id=user_id,
                category=category,
                version=result["version"],
            )

            return UserSettings.from_dict(result)

        except Exception as e:
            logger.error(
                "Update user settings failed",
                user_id=user_id,
                category=category,
                error=str(e),
            )
            raise


class GetUserSettings:
    """Use case for getting user settings"""

    def __init__(self, usersettings_port: UserSettingsPort):
        self.usersettings_port = usersettings_port

    async def execute(self, user_id: str, category: str | None = None) -> UserSettings | UserSettingsCollection:
        """
        Get user settings

        Args:
            user_id: User ID to get settings for
            category: Specific category, or None for all

        Returns:
            UserSettings entity if category specified, UserSettingsCollection if getting all
        """
        try:
            logger.info(
                "Getting user settings",
                user_id=user_id,
                category=category,
            )

            if category:
                # Get specific category
                result = await self.usersettings_port.get_settings(user_id, category)
                if not result:
                    # Return default empty settings
                    return UserSettings(
                        user_id=user_id,
                        category=category,
                        data={},
                        version=0,
                    )
                return UserSettings.from_dict(result)
            else:
                # Get all settings
                settings_list = await self.usersettings_port.get_all_settings(user_id)
                return UserSettingsCollection.from_settings_list(user_id, settings_list)

        except Exception as e:
            logger.error(
                "Get user settings failed",
                user_id=user_id,
                category=category,
                error=str(e),
            )
            raise
