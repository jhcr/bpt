# Assumptions:
# - FastAPI application setup with middleware and routes
# - Health check endpoint for Kubernetes
# - Structured logging and telemetry integration

import os
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework.config.env.env import get_env
from framework.logging.setup import setup_logging
from framework.telemetry.otel import setup_telemetry

from domain.errors import EventsError
from infrastructure.adapters.kafka.kafka_consumer import KafkaEventConsumer
from infrastructure.adapters.kafka.kafka_producer import KafkaEventProducer
from infrastructure.adapters.redis.redis_event_store import RedisEventStore
from presentation.api.event_routes import router as event_router
from presentation.middleware.errors import (
    domain_error_handler,
    general_exception_handler,
    validation_error_handler,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Events Service")
    setup_logging("events-service")
    setup_telemetry("events-service")

    # Initialize Kafka producer
    kafka_producer = KafkaEventProducer()
    await kafka_producer.start()
    app.state.kafka_producer = kafka_producer

    # Initialize Kafka consumer
    kafka_consumer = KafkaEventConsumer()
    app.state.kafka_consumer = kafka_consumer

    # Initialize Redis event store (optional)
    use_event_store = get_env("USE_EVENT_STORE", "true").lower() == "true"
    if use_event_store:
        redis_event_store = RedisEventStore()
        await redis_event_store.connect()
        app.state.redis_event_store = redis_event_store
    else:
        app.state.redis_event_store = None

    logger.info("Events Service started with Kafka and Redis connections")

    yield

    # Shutdown
    logger.info("Shutting down Events Service")

    # Cleanup resources
    if hasattr(app.state, "kafka_producer"):
        await app.state.kafka_producer.stop()

    if hasattr(app.state, "kafka_consumer"):
        await app.state.kafka_consumer.shutdown()

    if hasattr(app.state, "redis_event_store") and app.state.redis_event_store:
        await app.state.redis_event_store.disconnect()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Events Service",
        description="Event publishing, consumption, and replay service",
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

    # Exception handlers
    app.add_exception_handler(EventsError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Routes
    app.include_router(event_router)

    # Root health check
    @app.get("/")
    async def root():
        return {"service": "events-service", "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready():
        # Add dependency checks here (Kafka, Redis, etc.)
        return {"status": "ready"}

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(
            "Request received",
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
        )

        response = await call_next(request)

        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
        )

        return response

    return app


# Application instance
app = create_app()
