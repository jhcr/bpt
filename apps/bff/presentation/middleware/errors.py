import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware for BFF"""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise

        except ValueError as e:
            logger.warning("Validation error", error=str(e))
            return JSONResponse(status_code=400, content={"detail": str(e)})

        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
