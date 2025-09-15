# Assumptions:
# - ES256 keys are stored in environment variables or files
# - Redis connection URL is provided via environment
# - Cognito configuration is available in environment
# - Service runs on port 8080 by default

import os

# Shared imports
import sys

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "framework.modules"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from framework.config.env import get_auth_config, get_common_config
from framework.logging.setup import CorrelationMiddleware, setup_logging
from framework.telemetry.otel import setup_telemetry

from infrastructure.adapters.crypto.cipher_service_adapter import CipherServiceAdapter
from infrastructure.adapters.crypto.es256_signer import ES256Signer
from infrastructure.adapters.crypto.jwt_signer_adapter import JWTSignerAdapter
from infrastructure.adapters.redis.session_repository import (
    RedisCipherSessionRepository,
    RedisSessionRepository,
)
from infrastructure.factories.cognito_client_factory import CognitoClientFactory

# Local imports
from presentation.api.auth_routes import router as auth_router
from presentation.api.jwks_routes import router as jwks_router
from presentation.api.svc_token_routes import router as svc_token_router
from presentation.middleware.errors import ErrorHandlingMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    # Get configuration
    common_config = get_common_config()
    auth_config = get_auth_config()

    # Setup logging
    setup_logging(
        service_name="auth-service",
        level=common_config["log_level"],
        format_type="json" if not common_config["debug"] else "console",
    )

    logger = structlog.get_logger(__name__)
    logger.info("Starting auth service", config=common_config)

    # Create FastAPI app
    app = FastAPI(
        title="Auth Service",
        description="Authentication service with JWT and service tokens",
        version="1.0.0",
        debug=common_config["debug"],
    )

    # Setup telemetry
    setup_telemetry(service_name="auth-service", app=app)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "https://app.example.com",
        ],  # Frontend URLs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add correlation middleware
    app.add_middleware(CorrelationMiddleware)

    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Initialize dependencies on startup
    @app.on_event("startup")
    async def startup_event():
        logger.info("Initializing auth service dependencies")

        try:
            # Initialize Redis
            redis_client = redis.from_url(auth_config["redis_url"])
            await redis_client.ping()

            # Create repositories
            session_repo = RedisSessionRepository(redis_client)
            cipher_session_repo = RedisCipherSessionRepository(redis_client)

            # Initialize JWT signer
            # In production, load from AWS Secrets Manager or KMS
            private_key_pem = os.getenv("JWT_PRIVATE_KEY_PEM", _get_default_private_key())
            kid = os.getenv("JWT_KID", "2025-09-rotA")

            jwt_signer = ES256Signer(
                kid=kid,
                pem=(private_key_pem.encode() if isinstance(private_key_pem, str) else private_key_pem),
                iss=auth_config["jwt_issuer"],
                aud=auth_config["jwt_audience"],
            )

            # Create adapter instances
            cipher_service = CipherServiceAdapter()
            jwt_signer_adapter = JWTSignerAdapter(jwt_signer)
            cognito_client = CognitoClientFactory.create_client(
                user_pool_id=auth_config["cognito_user_pool_id"],
                client_id=auth_config["cognito_client_id"],
                client_secret=auth_config["cognito_client_secret"],
                region=auth_config.get("aws_region", "us-east-1"),
            )

            # Store dependencies in app state
            app.state.redis = redis_client
            app.state.session_repo = session_repo
            app.state.cipher_session_repo = cipher_session_repo
            app.state.jwt_signer = jwt_signer
            app.state.auth_config = auth_config
            app.state.cipher_service = cipher_service
            app.state.jwt_signer_adapter = jwt_signer_adapter
            app.state.cognito_client = cognito_client

            logger.info("Auth service dependencies initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize dependencies", error=str(e))
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down auth service")

        try:
            if hasattr(app.state, "redis"):
                await app.state.redis.close()

            logger.info("Auth service shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

    # Health check endpoints
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy", "service": "auth-service"}

    @app.get("/api/v1/health/ready")
    async def readiness_check(request: Request):
        try:
            # Check Redis connection
            await request.app.state.redis.ping()
            return {"status": "ready", "checks": {"redis": "ok"}}
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return {"status": "not_ready", "checks": {"redis": "failed"}}, 503

    @app.get("/api/v1/health/live")
    async def liveness_check():
        return {"status": "alive"}

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(jwks_router, prefix="/auth", tags=["jwks"])
    app.include_router(svc_token_router, prefix="/auth", tags=["service-tokens"])

    return app


def _get_default_private_key() -> str:
    """Get default ES256 private key for development"""
    # This is a development key - DO NOT use in production
    return """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQghLukC5v0Wd10guPz
FAqU0PYT+1HaUyM0Y6YOjkleI4OhRANCAAT/NZaWjpA5UZU5ZGPlx9ZZknqpFbIO
R+6TdBOkupHfXVwc2QZrz9fil7a8oWZKnB9efIbQxui9Sn3E45RoLCkB
-----END PRIVATE KEY-----"""


# Create the app instance
app = create_app()
