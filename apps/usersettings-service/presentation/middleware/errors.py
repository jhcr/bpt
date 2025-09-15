# Assumptions:
# - Global error handling middleware for FastAPI
# - Structured logging for all errors
# - Consistent error response format

import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

from domain.errors import UserSettingsError, VersionConflictError, UserSettingNotFoundError

logger = structlog.get_logger(__name__)


async def user_settings_exception_handler(request: Request, exc: UserSettingsError) -> JSONResponse:
    """Handle UserSettings domain exceptions"""
    logger.warning("Domain error", error=str(exc), type=type(exc).__name__)

    if isinstance(exc, UserSettingNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": str(exc),
                "code": "USER_SETTING_NOT_FOUND",
                "details": {"user_id": exc.user_id, "category": exc.category},
            },
        )
    elif isinstance(exc, VersionConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "error": str(exc),
                "code": "VERSION_CONFLICT",
                "details": {
                    "user_id": exc.user_id,
                    "category": exc.category,
                    "expected_version": exc.expected_version,
                    "actual_version": exc.actual_version,
                },
            },
        )
    else:
        return JSONResponse(status_code=400, content={"error": str(exc), "code": "DOMAIN_ERROR"})


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        type=type(exc).__name__,
        traceback=traceback.format_exc(),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(status_code=500, content={"error": "Internal server error", "code": "INTERNAL_ERROR"})


def install_error_handlers(app: FastAPI) -> None:
    """Install error handlers on FastAPI app"""
    app.add_exception_handler(UserSettingsError, user_settings_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
