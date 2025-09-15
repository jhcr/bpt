# Assumptions:
# - DynamoDB table name is configurable via environment
# - Using boto3 for DynamoDB operations
# - OCC (Optimistic Concurrency Control) via version field
# - Standard error handling with ClientError

import boto3
from datetime import datetime as dt
from typing import List
from botocore.exceptions import ClientError
import structlog

from application.ports.user_settings_repository import UserSettingsRepository
from domain.entities.user_setting import UserSetting
from domain.errors import VersionConflictError

logger = structlog.get_logger(__name__)


class DdbSettingsRepository(UserSettingsRepository):
    """DynamoDB repository for user settings with optimistic concurrency control"""

    def __init__(self, table_name: str, dynamodb_resource=None):
        if dynamodb_resource:
            self.t = dynamodb_resource.Table(table_name)
        else:
            self.t = boto3.resource("dynamodb").Table(table_name)

    async def get_setting(self, user_id: str, category: str) -> UserSetting | None:
        """Get user setting by user_id and category"""
        try:
            response = self.t.get_item(Key={"user_id": user_id, "category": category}, ConsistentRead=True)
            item = response.get("Item")

            if not item:
                return None

            return UserSetting(
                user_id=item["user_id"],
                category=item["category"],
                data=item["data"],
                version=item.get("version", 0),
                created_at=dt.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                updated_at=dt.fromisoformat(item["updated_at"]) if item.get("updated_at") else None,
                ttl_epoch_s=item.get("ttl_epoch_s"),
            )
        except Exception as e:
            logger.error("Failed to get setting", user_id=user_id, category=category, error=str(e))
            raise

    async def get_all_settings(self, user_id: str) -> List[UserSetting]:
        """Get all settings for a user"""
        try:
            response = self.t.query(
                KeyConditionExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id}
            )

            settings = []
            for item in response.get("Items", []):
                setting = UserSetting(
                    user_id=item["user_id"],
                    category=item["category"],
                    data=item["data"],
                    version=item.get("version", 0),
                    created_at=dt.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                    updated_at=dt.fromisoformat(item["updated_at"]) if item.get("updated_at") else None,
                    ttl_epoch_s=item.get("ttl_epoch_s"),
                )
                settings.append(setting)

            return settings
        except Exception as e:
            logger.error("Failed to get all settings", user_id=user_id, error=str(e))
            raise

    async def save_setting(self, setting: UserSetting, expected_version: int | None = None) -> UserSetting:
        """Save user setting with optimistic concurrency control"""
        try:
            now = dt.utcnow()
            now_iso = now.isoformat()

            if expected_version is None:
                # New setting
                expr = "SET #d=:d, #u=:u, #c=:c, #v=:v"
                cond = "attribute_not_exists(#v)"
                attr_values = {":d": setting.data, ":u": now_iso, ":c": now_iso, ":v": 1}
            else:
                # Update existing
                expr = "SET #d=:d, #u=:u, #v=:v"
                cond = "#v = :ev"
                attr_values = {":d": setting.data, ":u": now_iso, ":v": setting.version, ":ev": expected_version}

            # Add TTL if specified
            if setting.ttl_epoch_s:
                expr += ", #t=:t"
                attr_values[":t"] = setting.ttl_epoch_s

            response = self.t.update_item(
                Key={"user_id": setting.user_id, "category": setting.category},
                UpdateExpression=expr,
                ConditionExpression=cond,
                ExpressionAttributeNames={
                    "#d": "data",
                    "#u": "updated_at",
                    "#v": "version",
                    "#c": "created_at",
                    "#t": "ttl_epoch_s",
                },
                ExpressionAttributeValues=attr_values,
                ReturnValues="ALL_NEW",
            )

            item = response["Attributes"]
            return UserSetting(
                user_id=item["user_id"],
                category=item["category"],
                data=item["data"],
                version=item["version"],
                created_at=dt.fromisoformat(item["created_at"]),
                updated_at=dt.fromisoformat(item["updated_at"]),
                ttl_epoch_s=item.get("ttl_epoch_s"),
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Get current version for error
                current = await self.get_setting(setting.user_id, setting.category)
                current_version = current.version if current else 0
                raise VersionConflictError(setting.user_id, setting.category, expected_version or 0, current_version)
            logger.error(
                "DynamoDB error saving setting", user_id=setting.user_id, category=setting.category, error=str(e)
            )
            raise
        except Exception as e:
            logger.error("Failed to save setting", user_id=setting.user_id, category=setting.category, error=str(e))
            raise

    async def delete_setting(self, user_id: str, category: str) -> bool:
        """Delete user setting"""
        try:
            response = self.t.delete_item(Key={"user_id": user_id, "category": category}, ReturnValues="ALL_OLD")
            return "Attributes" in response
        except Exception as e:
            logger.error("Failed to delete setting", user_id=user_id, category=category, error=str(e))
            raise

    async def delete_all_settings(self, user_id: str) -> int:
        """Delete all settings for a user"""
        try:
            # First get all settings to delete
            settings = await self.get_all_settings(user_id)
            count = 0

            for setting in settings:
                if await self.delete_setting(user_id, setting.category):
                    count += 1

            return count
        except Exception as e:
            logger.error("Failed to delete all settings", user_id=user_id, error=str(e))
            raise
