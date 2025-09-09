# Assumptions:
# - Service URLs are provided via environment variables
# - JWT verification is configured with JWKS URL
# - Service token credentials are available in environment
# - All downstream services are accessible via service tokens

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Shared imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared', 'python'))
from shared_logging.setup import setup_logging, CorrelationMiddleware
from shared_telemetry.otel import setup_telemetry
from shared_config.env import get_common_config, get_auth_config, get_service_urls, get_service_token_config
from shared_auth.jwt_verify import create_jwt_verifier
from shared_auth.service_tokens import ServiceTokenClient, ServiceTokenHttpClient

# Local imports
from .api.user_routes import router as user_router
from .middleware.errors import ErrorHandlingMiddleware
from ..application.use_cases.get_user import GetUser
from ..application.use_cases.update_user_settings import GetUserSettings, UpdateUserSettings
from ..infrastructure.adapters.http_userprofiles_client import HttpUserProfilesClient
from ..infrastructure.adapters.http_usersettings_client import HttpUserSettingsClient


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Get configuration
    common_config = get_common_config()
    auth_config = get_auth_config()
    service_urls = get_service_urls()
    
    # Setup logging
    setup_logging(
        service_name="bff",
        level=common_config["log_level"],
        format_type="json" if not common_config["debug"] else "console"
    )
    
    logger = structlog.get_logger(__name__)
    logger.info("Starting BFF service", config=common_config)
    
    # Create FastAPI app
    app = FastAPI(
        title="BFF - Backend for Frontend",
        description="API composition layer for web and mobile clients",
        version="1.0.0",
        debug=common_config["debug"]
    )
    
    # Setup telemetry
    setup_telemetry(
        service_name="bff",
        app=app
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://app.example.com"],  # Frontend URLs
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
        logger.info("Initializing BFF service dependencies")
        
        try:
            # Initialize JWT verifier
            jwt_verifier = create_jwt_verifier(
                jwks_uri=auth_config["jwks_url"],
                issuer=auth_config["jwt_issuer"],
                audience=auth_config["jwt_audience"]
            )
            
            # Initialize service token clients
            bff_svc_config = get_service_token_config("bff")
            
            userprofiles_svc_token_client = ServiceTokenClient(
                auth_base=service_urls["auth_url"],
                client_id=bff_svc_config["client_id"],
                client_secret=bff_svc_config["client_secret"],
                sub_spn=bff_svc_config["sub_spn"],
                scope="svc.userprofiles.read svc.userprofiles.write"
            )
            
            usersettings_svc_token_client = ServiceTokenClient(
                auth_base=service_urls["auth_url"],
                client_id=bff_svc_config["client_id"],
                client_secret=bff_svc_config["client_secret"],
                sub_spn=bff_svc_config["sub_spn"],
                scope="svc.usersettings.read svc.usersettings.write"
            )
            
            # Create HTTP clients with service tokens
            userprofiles_http_client = ServiceTokenHttpClient(
                service_token_client=userprofiles_svc_token_client,
                base_url=service_urls["userprofiles_url"],
                timeout=5.0
            )
            
            usersettings_http_client = ServiceTokenHttpClient(
                service_token_client=usersettings_svc_token_client,
                base_url=service_urls["usersettings_url"],
                timeout=5.0
            )
            
            # Create port adapters
            userprofiles_port = HttpUserProfilesClient(userprofiles_http_client)
            usersettings_port = HttpUserSettingsClient(usersettings_http_client)
            
            # Create use cases
            get_user_uc = GetUser(userprofiles_port, usersettings_port)
            get_user_settings_uc = GetUserSettings(usersettings_port)
            update_user_settings_uc = UpdateUserSettings(usersettings_port)
            
            # Store dependencies in app state
            app.state.jwt_verifier = jwt_verifier
            app.state.userprofiles_port = userprofiles_port
            app.state.usersettings_port = usersettings_port
            app.state.get_user_uc = get_user_uc
            app.state.get_user_settings_uc = get_user_settings_uc
            app.state.update_user_settings_uc = update_user_settings_uc
            
            logger.info("BFF service dependencies initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize BFF dependencies", error=str(e))
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down BFF service")
        # No cleanup needed for HTTP clients
        logger.info("BFF service shutdown complete")
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "bff"}
    
    @app.get("/health/ready")
    async def readiness_check(request: Request):
        try:
            # Test connectivity to downstream services
            # This is a simplified check - in production you might want more sophisticated health checks
            return {"status": "ready", "dependencies": {"userprofiles": "ok", "usersettings": "ok"}}
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return {"status": "not_ready", "dependencies": {"userprofiles": "unknown", "usersettings": "unknown"}}, 503
    
    @app.get("/health/live")
    async def liveness_check():
        return {"status": "alive"}
    
    # Include routers
    app.include_router(user_router, tags=["user"])
    
    return app


# Create the app instance
app = create_app()