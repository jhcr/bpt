# Assumptions:
# - Full FastAPI application for user profiles
# - Clean Architecture with dependency injection
# - PostgreSQL database integration
# - Health check and user management endpoints

import os
import sys
from contextlib import asynccontextmanager

import psycopg_pool
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from framework.logging.setup import setup_logging
from framework.telemetry.otel import setup_telemetry

from application.use_cases.create_user import CreateUser
from application.use_cases.get_user import GetUser
from application.use_cases.list_users import ListUsers
from application.use_cases.update_user import UpdateUser
from infrastructure.adapters.pg_user_repository import PgUserRepository
from infrastructure.config.settings import get_settings
from presentation.api.health_routes import router as health_router
from presentation.api.user_routes import router as user_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    setup_logging("userprofiles-service", format_type="json")
    setup_telemetry("userprofiles-service", app=app)

    # Initialize dependencies
    settings = get_settings()

    # Create database connection pool
    db_pool = psycopg_pool.AsyncConnectionPool(conninfo=settings.pg_dsn, min_size=2, max_size=10, open=False)
    await db_pool.open()

    # Create repository with connection pool
    user_repository = PgUserRepository(db_pool=db_pool)

    # Create use cases
    get_user_uc = GetUser(user_repository=user_repository)
    create_user_uc = CreateUser(user_repository=user_repository)
    update_user_uc = UpdateUser(user_repository=user_repository)
    list_users_uc = ListUsers(user_repository=user_repository)

    # Store dependencies in app state
    app.state.settings = settings
    app.state.db_pool = db_pool
    app.state.user_repository = user_repository
    app.state.get_user_uc = get_user_uc
    app.state.create_user_uc = create_user_uc
    app.state.update_user_uc = update_user_uc
    app.state.list_users_uc = list_users_uc

    logger.info("UserProfiles service starting up")

    yield

    # Shutdown
    logger.info("UserProfiles service shutting down")
    if hasattr(app.state, "db_pool"):
        await app.state.db_pool.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="User Profiles Service",
        description="User profile management service with PostgreSQL storage",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(user_router, prefix="/api/v1")

    return app


# Create app instance
app = create_app()
