# Assumptions:
# - FastAPI application factory pattern
# - Dependency injection with container
# - Structured logging and telemetry initialization

import os
import sys
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from framework.logging.setup import setup_logging
from framework.telemetry.otel import setup_telemetry
from infrastructure.config.settings import get_settings
from infrastructure.adapters.ddb_settings_repository import DdbSettingsRepository
from application.use_cases.get_user_setting import GetUserSetting
from application.use_cases.get_all_user_settings import GetAllUserSettings
from application.use_cases.update_user_setting import UpdateUserSetting
from application.use_cases.delete_user_setting import DeleteUserSetting, DeleteAllUserSettings
from presentation.api.health_routes import router as health_router
from presentation.api.settings_routes import router as settings_router
from presentation.middleware.errors import install_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging("usersettings-service", format_type="json")
    setup_telemetry("usersettings-service", app=app)

    settings = get_settings()
    logger = structlog.get_logger(__name__)

    # Create DynamoDB client (singleton)
    dynamodb_resource = boto3.resource(
        "dynamodb",
        region_name=settings.dynamodb_region,
        endpoint_url=settings.dynamodb_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    # Create repository
    user_settings_repository = DdbSettingsRepository(
        table_name=settings.dynamodb_table_user_settings, dynamodb_resource=dynamodb_resource
    )

    # Create use cases
    get_user_setting_uc = GetUserSetting(repository=user_settings_repository)
    get_all_user_settings_uc = GetAllUserSettings(repository=user_settings_repository)
    update_user_setting_uc = UpdateUserSetting(repository=user_settings_repository)
    delete_user_setting_uc = DeleteUserSetting(repository=user_settings_repository)
    delete_all_user_settings_uc = DeleteAllUserSettings(repository=user_settings_repository)

    # Store dependencies in app state
    app.state.settings = settings
    app.state.dynamodb_resource = dynamodb_resource
    app.state.user_settings_repository = user_settings_repository
    app.state.get_user_setting_uc = get_user_setting_uc
    app.state.get_all_user_settings_uc = get_all_user_settings_uc
    app.state.update_user_setting_uc = update_user_setting_uc
    app.state.delete_user_setting_uc = delete_user_setting_uc
    app.state.delete_all_user_settings_uc = delete_all_user_settings_uc

    logger.info(
        "Starting UserSettings service", service=settings.service_name, env=settings.env, port=settings.service_port
    )

    yield

    # Shutdown
    logger.info("Shutting down UserSettings service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="UserSettings Service",
        description="User settings management microservice with DynamoDB storage",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Install error handlers
    install_error_handlers(app)

    # Include routers
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(settings_router, tags=["User Settings"])

    return app


# Create app instance
app = create_app()
