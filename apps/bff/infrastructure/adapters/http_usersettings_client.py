from typing import Optional, Dict, Any, List
import structlog

from ....shared.python.shared_auth.service_tokens import ServiceTokenHttpClient
from ...application.ports.usersettings_port import UserSettingsPort

logger = structlog.get_logger(__name__)


class HttpUserSettingsClient(UserSettingsPort):
    """HTTP client for UserSettings service using service tokens"""
    
    def __init__(self, service_token_client: ServiceTokenHttpClient):
        self.client = service_token_client
    
    async def get_settings(self, user_id: str, category: str) -> Optional[Dict[str, Any]]:
        """Get user settings for a specific category"""
        try:
            response = await self.client.get(
                f"/internal/users/{user_id}/settings/{category}"
            )
            
            if response.status_code == 404:
                return None
            
            data = response.json()
            logger.debug("User settings retrieved", user_id=user_id, category=category)
            return data
            
        except Exception as e:
            logger.error("Failed to get user settings", 
                        user_id=user_id, category=category, error=str(e))
            raise
    
    async def get_all_settings(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all settings for a user"""
        try:
            response = await self.client.get(f"/internal/users/{user_id}/settings")
            
            if response.status_code == 404:
                return []
            
            data = response.json()
            settings_list = data.get("settings", [])
            
            logger.debug("All user settings retrieved", 
                        user_id=user_id, count=len(settings_list))
            return settings_list
            
        except Exception as e:
            logger.error("Failed to get all user settings", user_id=user_id, error=str(e))
            raise
    
    async def update_settings(
        self,
        user_id: str,
        category: str,
        data: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user settings with optimistic concurrency control"""
        try:
            payload = {
                "data": data
            }
            
            if expected_version is not None:
                payload["expected_version"] = expected_version
            
            response = await self.client.put(
                f"/internal/users/{user_id}/settings/{category}",
                json=payload
            )
            
            if response.status_code == 404:
                return None
            
            if response.status_code == 409:
                # Version conflict
                logger.warning("Settings update version conflict", 
                              user_id=user_id, category=category, 
                              expected_version=expected_version)
                return None
            
            result = response.json()
            logger.info("User settings updated", 
                       user_id=user_id, category=category, 
                       version=result.get("version"))
            return result
            
        except Exception as e:
            logger.error("Failed to update user settings", 
                        user_id=user_id, category=category, error=str(e))
            raise
    
    async def delete_settings(self, user_id: str, category: str) -> bool:
        """Delete user settings for a category"""
        try:
            response = await self.client.delete(
                f"/internal/users/{user_id}/settings/{category}"
            )
            
            deleted = response.status_code == 200 or response.status_code == 204
            logger.info("User settings delete result", 
                       user_id=user_id, category=category, deleted=deleted)
            return deleted
            
        except Exception as e:
            logger.error("Failed to delete user settings", 
                        user_id=user_id, category=category, error=str(e))
            raise
    
    async def delete_all_settings(self, user_id: str) -> int:
        """Delete all settings for a user, return count deleted"""
        try:
            response = await self.client.delete(f"/internal/users/{user_id}/settings")
            
            if response.status_code == 404:
                return 0
            
            result = response.json()
            count = result.get("deleted_count", 0)
            
            logger.info("All user settings deleted", user_id=user_id, count=count)
            return count
            
        except Exception as e:
            logger.error("Failed to delete all user settings", user_id=user_id, error=str(e))
            raise