# Assumptions:
# - UserSetting entity represents a category of settings for a user
# - Version field for optimistic concurrency control
# - Data field contains the actual settings as dict

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class UserSetting:
    """User setting entity for a specific category"""

    user_id: str
    category: str
    data: dict[str, Any]
    version: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    ttl_epoch_s: int | None = None  # TTL for DynamoDB

    def increment_version(self) -> "UserSetting":
        """Create new instance with incremented version"""
        return UserSetting(
            user_id=self.user_id,
            category=self.category,
            data=self.data,
            version=self.version + 1,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            ttl_epoch_s=self.ttl_epoch_s,
        )

    def update_data(self, new_data: dict[str, Any]) -> "UserSetting":
        """Create new instance with updated data and incremented version"""
        return UserSetting(
            user_id=self.user_id,
            category=self.category,
            data=new_data,
            version=self.version + 1,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            ttl_epoch_s=self.ttl_epoch_s,
        )

    @classmethod
    def create_new(
        cls, user_id: str, category: str, data: dict[str, Any], ttl_epoch_s: int | None = None
    ) -> "UserSetting":
        """Create new user setting"""
        now = datetime.utcnow()
        return cls(
            user_id=user_id,
            category=category,
            data=data,
            version=1,
            created_at=now,
            updated_at=now,
            ttl_epoch_s=ttl_epoch_s,
        )
