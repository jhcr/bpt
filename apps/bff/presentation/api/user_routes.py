from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from framework.auth.principals import Principal

from application.use_cases.get_user import GetUser
from application.use_cases.update_user_settings import (
    GetUserSettings,
    UpdateUserSettings,
)
from presentation.middleware.auth_jwt import (
    require_user_read,
    require_usersettings_read,
    require_usersettings_write,
)
from presentation.schema.user_schemas import (
    UpdateUserSettingsRequest,
    UserResponse,
    UserSettingsResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


def get_get_user_use_case(request) -> GetUser:
    """Dependency to get GetUser use case"""
    return request.app.state.get_user_uc


def get_get_user_settings_use_case(request) -> GetUserSettings:
    """Dependency to get GetUserSettings use case"""
    return request.app.state.get_user_settings_uc


def get_update_user_settings_use_case(request) -> UpdateUserSettings:
    """Dependency to get UpdateUserSettings use case"""
    return request.app.state.update_user_settings_uc


@router.get("/api/v1/user", response_model=UserResponse)
async def get_current_user(
    principal: Principal = require_user_read,
    get_user_uc: GetUser = Depends(get_get_user_use_case),
):
    """Get current user profile with settings"""
    try:
        # Extract user_sub from principal
        user_sub = principal.get_actor_sub() or principal.sub

        user_data = await get_user_uc.execute(user_sub=user_sub)

        logger.info("User profile retrieved", user_id=user_data["id"])
        return UserResponse(**user_data)

    except ValueError as e:
        logger.warning("User not found", error=str(e))
        raise HTTPException(status_code=404, detail="User not found") from e
    except Exception as e:
        logger.error("Get user failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get user") from e


@router.get("/api/v1/user/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    category: str | None = None,
    principal: Principal = require_usersettings_read,
    get_settings_uc: GetUserSettings = Depends(get_get_user_settings_use_case),
):
    """Get user settings (specific category or all)"""
    try:
        # Get user ID from principal
        user_sub = principal.get_actor_sub() or principal.sub

        # For BFF, we need to map cognito_sub to user_id
        # This requires a call to UserProfiles service first
        # For now, we'll use the sub as user_id (this should be improved)

        settings_data = await get_settings_uc.execute(
            user_id=user_sub,  # This should be mapped from cognito_sub to internal user_id
            category=category,
        )

        logger.info("User settings retrieved", user_id=user_sub, category=category)
        return UserSettingsResponse(**settings_data)

    except Exception as e:
        logger.error("Get user settings failed", category=category, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get user settings") from e


@router.put("/api/v1/user/settings/{category}", response_model=dict[str, Any])
async def update_user_settings(
    category: str,
    request_data: UpdateUserSettingsRequest,
    principal: Principal = require_usersettings_write,
    update_settings_uc: UpdateUserSettings = Depends(get_update_user_settings_use_case),
):
    """Update user settings for a specific category"""
    try:
        # Get user ID from principal
        user_sub = principal.get_actor_sub() or principal.sub

        # For BFF, we need to map cognito_sub to user_id
        # For now, we'll use the sub as user_id (this should be improved)

        result = await update_settings_uc.execute(
            user_id=user_sub,  # This should be mapped from cognito_sub to internal user_id
            category=category,
            settings_data=request_data.data,
            expected_version=request_data.expected_version,
        )

        logger.info("User settings updated", user_id=user_sub, category=category)
        return result

    except ValueError as e:
        if "version conflict" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="Version conflict - settings were modified by another process",
            ) from e
        logger.warning("Update settings validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Update user settings failed", category=category, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update user settings") from e
