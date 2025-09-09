from typing import Dict, Any, Optional
import structlog

from ..ports.usersettings_port import UserSettingsPort
from ....shared.python.shared_auth.principals import Principal

logger = structlog.get_logger(__name__)


class UpdateUserSettings:
    """Use case for updating user settings"""
    
    def __init__(self, usersettings_port: UserSettingsPort):
        self.usersettings_port = usersettings_port
    
    async def execute(
        self,
        principal: Principal,
        user_id: str,
        category: str,
        settings_data: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update user settings
        
        Args:
            principal: Authenticated principal
            user_id: User ID to update settings for
            category: Settings category
            settings_data: Settings data to update
            expected_version: Expected version for optimistic locking
            
        Returns:
            Updated settings data
        """
        try:
            # Verify principal has access to this user
            actor_sub = principal.get_actor_sub()
            if not actor_sub:
                raise ValueError("No acting user found")
            
            logger.info("Updating user settings", 
                       user_id=user_id, category=category, actor_sub=actor_sub)
            
            # Update settings
            result = await self.usersettings_port.update_settings(
                user_id=user_id,
                category=category,
                data=settings_data,
                expected_version=expected_version
            )
            
            if not result:
                logger.warning("Settings update failed", 
                             user_id=user_id, category=category)
                raise ValueError("Failed to update settings - version conflict or user not found")
            
            logger.info("User settings updated successfully", 
                       user_id=user_id, category=category, version=result["version"])
            
            return {
                "user_id": result["user_id"],
                "category": result["category"],
                "data": result["data"],
                "version": result["version"],
                "updated_at": result.get("updated_at")
            }
            
        except Exception as e:
            logger.error("Update user settings failed", 
                        user_id=user_id, category=category, error=str(e))
            raise


class GetUserSettings:
    """Use case for getting user settings"""
    
    def __init__(self, usersettings_port: UserSettingsPort):
        self.usersettings_port = usersettings_port
    
    async def execute(
        self,
        principal: Principal,
        user_id: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user settings
        
        Args:
            principal: Authenticated principal
            user_id: User ID to get settings for
            category: Specific category, or None for all
            
        Returns:
            Settings data
        """
        try:
            # Verify principal has access to this user
            actor_sub = principal.get_actor_sub()
            if not actor_sub:
                raise ValueError("No acting user found")
            
            logger.info("Getting user settings", 
                       user_id=user_id, category=category, actor_sub=actor_sub)
            
            if category:
                # Get specific category
                result = await self.usersettings_port.get_settings(user_id, category)
                if not result:
                    return {
                        "user_id": user_id,
                        "category": category,
                        "data": {},
                        "version": 0
                    }
                return result
            else:
                # Get all settings
                settings_list = await self.usersettings_port.get_all_settings(user_id)
                
                # Group by category
                settings_by_category = {}
                for setting in settings_list:
                    settings_by_category[setting["category"]] = {
                        "data": setting["data"],
                        "version": setting["version"],
                        "updated_at": setting.get("updated_at")
                    }
                
                return {
                    "user_id": user_id,
                    "settings": settings_by_category
                }
            
        except Exception as e:
            logger.error("Get user settings failed", 
                        user_id=user_id, category=category, error=str(e))
            raise