"""Domain response models for BFF service"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class UserProfileResponse:
    """Response for user profile data"""

    user_id: str
    cognito_sub: str
    email: str
    given_name: str | None = None
    family_name: str | None = None
    preferred_username: str | None = None
    picture: str | None = None
    locale: str | None = None
    zoneinfo: str | None = None
    phone_number: str | None = None
    email_verified: bool = False
    phone_verified: bool = False
    user_status: str | None = None
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class CreateUserProfileResponse:
    """Response for user profile creation"""

    user_id: str
    cognito_sub: str
    email: str
    created_at: datetime


@dataclass(frozen=True)
class UpdateUserProfileResponse:
    """Response for user profile update"""

    user_id: str
    updated_at: datetime
    changes_made: list[str]


@dataclass(frozen=True)
class UserSettingValue:
    """Individual user setting value"""

    key: str
    value: Any
    value_type: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class UserSettingsResponse:
    """Response for user settings data"""

    user_id: str
    category: str
    settings: list[UserSettingValue]
    total_count: int = 0


@dataclass(frozen=True)
class UpdateUserSettingsResponse:
    """Response for user settings update"""

    user_id: str
    category: str
    updated_settings: list[str]
    updated_at: datetime
