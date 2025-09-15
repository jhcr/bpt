# Assumptions:
# - FastAPI routes for user settings CRUD operations
# - Service token authentication middleware
# - RESTful API design principles


from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
import structlog

from framework.auth.jwt_verify import JWTVerifier, create_jwt_verifier
from framework.auth.principals import Principal, create_service_principal
from application.use_cases.get_user_setting import GetUserSetting
from application.use_cases.get_all_user_settings import GetAllUserSettings
from application.use_cases.update_user_setting import UpdateUserSetting
from application.use_cases.delete_user_setting import DeleteUserSetting, DeleteAllUserSettings
from domain.errors import VersionConflictError
from presentation.schema.user_settings_schemas import (
    UpdateUserSettingRequest,
    UserSettingResponse,
    UserSettingsListResponse,
    DeleteUserSettingResponse,
    DeleteAllUserSettingsResponse,
    ErrorResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


# Dependency functions for FastAPI DI
def get_get_user_setting_use_case(request: Request) -> GetUserSetting:
    """Dependency to get GetUserSetting use case"""
    return request.app.state.get_user_setting_uc


def get_get_all_user_settings_use_case(request: Request) -> GetAllUserSettings:
    """Dependency to get GetAllUserSettings use case"""
    return request.app.state.get_all_user_settings_uc


def get_update_user_setting_use_case(request: Request) -> UpdateUserSetting:
    """Dependency to get UpdateUserSetting use case"""
    return request.app.state.update_user_setting_uc


def get_delete_user_setting_use_case(request: Request) -> DeleteUserSetting:
    """Dependency to get DeleteUserSetting use case"""
    return request.app.state.delete_user_setting_uc


def get_delete_all_user_settings_use_case(request: Request) -> DeleteAllUserSettings:
    """Dependency to get DeleteAllUserSettings use case"""
    return request.app.state.delete_all_user_settings_uc


def get_jwt_verifier() -> JWTVerifier:
    """Create JWT verifier instance for service tokens"""
    # In production, these would come from environment variables
    jwks_uri = "https://auth.example.com/.well-known/jwks.json"
    issuer = "https://auth.example.com"
    audience = "usersettings-service"

    return create_jwt_verifier(jwks_uri, issuer, audience)


def get_principal(
    credentials=Depends(security),
    jwt_verifier: JWTVerifier = Depends(get_jwt_verifier),
) -> Principal:
    """Dependency to get authenticated principal from service token"""
    try:
        token = credentials.credentials

        # Verify JWT token
        claims = jwt_verifier.verify(token)

        # Create service principal (this service should only accept service tokens)
        if claims.get("token_use") != "svc":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Service token required")

        return create_service_principal(claims)

    except Exception as e:
        logger.warning("Service token verification failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")


@router.get(
    "/internal/users/{user_id}/settings/{category}",
    response_model=UserSettingResponse,
    responses={404: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
async def get_user_setting(
    user_id: str,
    category: str,
    principal: Principal = Depends(get_principal),
    get_setting_uc: GetUserSetting = Depends(get_get_user_setting_use_case),
):
    """Get user setting by category"""
    try:
        logger.info("Getting user setting", user_id=user_id, category=category)

        setting = await get_setting_uc.execute(user_id, category)

        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting not found for user {user_id}, category {category}",
            )

        return UserSettingResponse(
            user_id=setting.user_id,
            category=setting.category,
            data=setting.data,
            version=setting.version,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )

    except Exception as e:
        logger.error("Failed to get user setting", user_id=user_id, category=category, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/internal/users/{user_id}/settings",
    response_model=UserSettingsListResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_all_user_settings(
    user_id: str,
    principal: Principal = Depends(get_principal),
    get_all_settings_uc: GetAllUserSettings = Depends(get_get_all_user_settings_use_case),
):
    """Get all settings for a user"""
    try:
        logger.info("Getting all user settings", user_id=user_id)

        settings = await get_all_settings_uc.execute(user_id)

        settings_response = [
            UserSettingResponse(
                user_id=setting.user_id,
                category=setting.category,
                data=setting.data,
                version=setting.version,
                created_at=setting.created_at,
                updated_at=setting.updated_at,
            )
            for setting in settings
        ]

        return UserSettingsListResponse(settings=settings_response, count=len(settings_response))

    except Exception as e:
        logger.error("Failed to get all user settings", user_id=user_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/internal/users/{user_id}/settings/{category}",
    response_model=UserSettingResponse,
    responses={409: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
async def update_user_setting(
    user_id: str,
    category: str,
    request: UpdateUserSettingRequest,
    principal: Principal = Depends(get_principal),
    update_setting_uc: UpdateUserSetting = Depends(get_update_user_setting_use_case),
):
    """Update user setting with optimistic concurrency control"""
    try:
        logger.info(
            "Updating user setting", user_id=user_id, category=category, expected_version=request.expected_version
        )

        setting = await update_setting_uc.execute(
            user_id=user_id, category=category, data=request.data, expected_version=request.expected_version
        )

        return UserSettingResponse(
            user_id=setting.user_id,
            category=setting.category,
            data=setting.data,
            version=setting.version,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )

    except VersionConflictError as e:
        logger.warning("Version conflict updating user setting", user_id=user_id, category=category, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version conflict: expected {e.expected_version}, actual {e.actual_version}",
        )
    except Exception as e:
        logger.error("Failed to update user setting", user_id=user_id, category=category, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/internal/users/{user_id}/settings/{category}",
    response_model=DeleteUserSettingResponse,
    responses={401: {"model": ErrorResponse}},
)
async def delete_user_setting(
    user_id: str,
    category: str,
    principal: Principal = Depends(get_principal),
    delete_setting_uc: DeleteUserSetting = Depends(get_delete_user_setting_use_case),
):
    """Delete user setting"""
    try:
        logger.info("Deleting user setting", user_id=user_id, category=category)

        deleted = await delete_setting_uc.execute(user_id, category)

        return DeleteUserSettingResponse(deleted=deleted, user_id=user_id, category=category)

    except Exception as e:
        logger.error("Failed to delete user setting", user_id=user_id, category=category, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/internal/users/{user_id}/settings",
    response_model=DeleteAllUserSettingsResponse,
    responses={401: {"model": ErrorResponse}},
)
async def delete_all_user_settings(
    user_id: str,
    principal: Principal = Depends(get_principal),
    delete_all_settings_uc: DeleteAllUserSettings = Depends(get_delete_all_user_settings_use_case),
):
    """Delete all settings for a user"""
    try:
        logger.info("Deleting all user settings", user_id=user_id)

        count = await delete_all_settings_uc.execute(user_id)

        return DeleteAllUserSettingsResponse(deleted_count=count, user_id=user_id)

    except Exception as e:
        logger.error("Failed to delete all user settings", user_id=user_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
