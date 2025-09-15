from typing import Any

import structlog
from framework.auth.service_tokens import ServiceTokenHttpClient

from application.ports.userprofiles_port import UserProfilesPort

logger = structlog.get_logger(__name__)


class HttpUserProfilesClient(UserProfilesPort):
    """HTTP client for UserProfiles service using service tokens"""

    def __init__(self, service_token_client: ServiceTokenHttpClient):
        self.client = service_token_client

    async def get_user_by_sub(self, cognito_sub: str) -> dict[str, Any] | None:
        """Get user profile by Cognito subject"""
        try:
            response = await self.client.get(f"/internal/users/by-sub/{cognito_sub}", actor_sub=cognito_sub)

            if response.status_code == 404:
                return None

            data = response.json()
            logger.debug("User profile retrieved by sub", cognito_sub=cognito_sub)
            return data

        except Exception as e:
            logger.error("Failed to get user by sub", cognito_sub=cognito_sub, error=str(e))
            raise

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user profile by internal ID"""
        try:
            response = await self.client.get(f"/internal/users/{user_id}")

            if response.status_code == 404:
                return None

            data = response.json()
            logger.debug("User profile retrieved by id", user_id=user_id)
            return data

        except Exception as e:
            logger.error("Failed to get user by id", user_id=user_id, error=str(e))
            raise

    async def create_user(
        self,
        cognito_sub: str,
        email: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> dict[str, Any]:
        """Create new user profile"""
        try:
            payload = {
                "cognito_sub": cognito_sub,
                "email": email,
            }

            if display_name:
                payload["display_name"] = display_name
            if avatar_url:
                payload["avatar_url"] = avatar_url

            response = await self.client.post("/internal/users", json=payload, actor_sub=cognito_sub)

            data = response.json()
            logger.info("User profile created", user_id=data.get("id"), cognito_sub=cognito_sub)
            return data

        except Exception as e:
            logger.error("Failed to create user", cognito_sub=cognito_sub, error=str(e))
            raise

    async def update_user(
        self,
        user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update user profile"""
        try:
            payload = {}

            if email is not None:
                payload["email"] = email
            if display_name is not None:
                payload["display_name"] = display_name
            if avatar_url is not None:
                payload["avatar_url"] = avatar_url
            if is_active is not None:
                payload["is_active"] = is_active

            if not payload:
                # No updates to make
                return await self.get_user_by_id(user_id)

            response = await self.client.put(f"/internal/users/{user_id}", json=payload)

            if response.status_code == 404:
                return None

            data = response.json()
            logger.info("User profile updated", user_id=user_id)
            return data

        except Exception as e:
            logger.error("Failed to update user", user_id=user_id, error=str(e))
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete user profile"""
        try:
            response = await self.client.delete(f"/internal/users/{user_id}")

            deleted = response.status_code == 200 or response.status_code == 204
            logger.info("User profile delete result", user_id=user_id, deleted=deleted)
            return deleted

        except Exception as e:
            logger.error("Failed to delete user", user_id=user_id, error=str(e))
            raise
