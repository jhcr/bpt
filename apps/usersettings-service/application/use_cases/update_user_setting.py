# Assumptions:
# - Use case for updating user settings with OCC
# - Creates new setting if doesn't exist
# - Handles version conflicts gracefully

from typing import Any

import structlog

from domain.entities.user_setting import UserSetting
from domain.errors import VersionConflictError
from application.ports.user_settings_repository import UserSettingsRepository

logger = structlog.get_logger(__name__)


class UpdateUserSetting:
    """Use case for updating user setting with optimistic concurrency control"""

    def __init__(self, repository: UserSettingsRepository):
        self.repository = repository

    async def execute(
        self, user_id: str, category: str, data: dict[str, Any], expected_version: int | None = None
    ) -> UserSetting:
        """
        Update user setting with optimistic concurrency control

        Args:
            user_id: User identifier
            category: Setting category
            data: Setting data
            expected_version: Expected current version for OCC (None for new setting)

        Returns:
            Updated UserSetting

        Raises:
            VersionConflictError: If expected_version doesn't match current version
        """
        try:
            logger.info("Updating user setting", user_id=user_id, category=category, expected_version=expected_version)

            if expected_version is None:
                # Creating new setting
                setting = UserSetting.create_new(user_id, category, data)
                logger.debug("Creating new user setting", user_id=user_id, category=category)
            else:
                # Updating existing setting
                current_setting = await self.repository.get_setting(user_id, category)

                if not current_setting:
                    # Setting doesn't exist, create new one
                    setting = UserSetting.create_new(user_id, category, data)
                    logger.debug("Setting not found, creating new", user_id=user_id, category=category)
                else:
                    # Update existing setting
                    setting = current_setting.update_data(data)
                    logger.debug(
                        "Updating existing setting",
                        user_id=user_id,
                        category=category,
                        current_version=current_setting.version,
                        new_version=setting.version,
                    )

            # Save with OCC
            updated_setting = await self.repository.save_setting(setting, expected_version)

            logger.info(
                "User setting updated successfully", user_id=user_id, category=category, version=updated_setting.version
            )

            return updated_setting

        except VersionConflictError:
            logger.warning(
                "Version conflict updating user setting",
                user_id=user_id,
                category=category,
                expected_version=expected_version,
            )
            raise
        except Exception as e:
            logger.error("Failed to update user setting", user_id=user_id, category=category, error=str(e))
            raise
