import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from domain.errors import (
    AuthDomainError,
    CipherSessionError,
    CognitoError,
    InvalidCredentialsError,
    InvalidSessionError,
    InvalidTokenError,
    JWTSigningError,
    ServiceTokenError,
    SessionExpiredError,
    UnauthorizedClientError,
    UserNotFoundError,
)

logger = structlog.get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise

        except InvalidCredentialsError as e:
            logger.warning("Invalid credentials", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

        except UnauthorizedClientError as e:
            logger.warning("Unauthorized client", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Unauthorized client"})

        except (InvalidSessionError, SessionExpiredError) as e:
            logger.warning("Session error", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})

        except InvalidTokenError as e:
            logger.warning("Token error", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        except UserNotFoundError as e:
            logger.warning("User not found", error=str(e))
            return JSONResponse(status_code=404, content={"detail": "User not found"})

        except CipherSessionError as e:
            logger.warning("Cipher session error", error=str(e))
            return JSONResponse(status_code=400, content={"detail": "Cipher session error"})

        except (ServiceTokenError, JWTSigningError) as e:
            logger.error("Service error", error=str(e))
            return JSONResponse(status_code=500, content={"detail": "Service error"})

        except CognitoError as e:
            logger.error("Cognito error", error=str(e))
            return JSONResponse(status_code=500, content={"detail": "Authentication service error"})

        except AuthDomainError as e:
            logger.error("Domain error", error=str(e))
            return JSONResponse(status_code=500, content={"detail": "Internal error"})

        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
