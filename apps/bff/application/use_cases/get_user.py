from typing import Dict, Any, Optional
import structlog

from ..ports.userprofiles_port import UserProfilesPort
from ..ports.usersettings_port import UserSettingsPort
from ...domain.entities.user import User
from ....shared.python.shared_auth.principals import Principal

logger = structlog.get_logger(__name__)


class GetUser:
    """Use case for getting user profile with settings"""
    
    def __init__(
        self,
        userprofiles_port: UserProfilesPort,
        usersettings_port: UserSettingsPort
    ):
        self.userprofiles_port = userprofiles_port
        self.usersettings_port = usersettings_port
    
    async def execute(self, principal: Principal) -> Dict[str, Any]:
        """
        Get user profile with settings
        
        Args:
            principal: Authenticated principal
            
        Returns:
            Dictionary with user data
        """
        try:
            user_sub = principal.get_actor_sub() or principal.sub
            
            logger.info("Getting user profile", user_sub=user_sub)
            
            # Get user profile from UserProfiles service
            profile_data = await self.userprofiles_port.get_user_by_sub(user_sub)
            
            if not profile_data:
                logger.warning("User profile not found", user_sub=user_sub)
                raise ValueError("User not found")
            
            # Get user settings from UserSettings service
            settings_data = None
            try:
                # Get general settings category
                settings_list = await self.usersettings_port.get_all_settings(profile_data["id"])
                
                # Combine all settings into a single dict
                combined_settings = {}
                for setting in settings_list:
                    combined_settings[setting["category"]] = setting["data"]
                
                if combined_settings:
                    settings_data = {"data": combined_settings}
                
            except Exception as e:
                logger.warning("Failed to get user settings", 
                             user_id=profile_data["id"], error=str(e))
                # Continue without settings - they're optional
            
            # Create aggregated user entity
            user = User.from_profile_and_settings(profile_data, settings_data)
            
            logger.info("User profile retrieved successfully", user_id=user.id)
            
            return {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "settings": user.settings or {}
            }
            
        except Exception as e:
            logger.error("Get user failed", user_sub=principal.get_actor_sub(), error=str(e))
            raise