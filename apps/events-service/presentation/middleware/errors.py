# Assumptions:
# - Global error handling middleware for FastAPI
# - Structured logging for errors
# - Consistent error response format

from datetime import datetime

import structlog
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.errors import (
    EventPublishError,
    EventReplayError,
    EventsError,
    EventValidationError,
)

logger = structlog.get_logger(__name__)


async def domain_error_handler(request: Request, exc: EventsError) -> JSONResponse:
    """Handle domain-specific errors"""
    logger.warning(
        "Domain error occurred",
        error_type=type(exc).__name__,
        error=str(exc),
        path=request.url.path,
    )

    # Map domain errors to HTTP status codes
    status_mapping = {EventValidationError: 400, EventPublishError: 500, EventReplayError: 500}

    status_code = status_mapping.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    logger.warning("Request validation failed", errors=exc.errors(), path=request.url.path)

    return JSONResponse(
        status_code=400,
        content={
            "error": "Request validation failed",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.info(
        "HTTP exception", status_code=exc.status_code, detail=exc.detail, path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )
