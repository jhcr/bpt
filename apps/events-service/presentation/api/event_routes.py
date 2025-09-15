# Assumptions:
# - FastAPI for REST endpoints
# - JWT middleware for authentication
# - Validation schemas for request/response
# - Event publishing and replay endpoints

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from framework.auth.principals import Principal

from application.use_cases.publish_event import PublishEvent
from application.use_cases.replay_events import ReplayEvents
from domain.entities.event import Event
from domain.errors import EventPublishError, EventReplayError, EventValidationError
from domain.value_objects.event_types import EventType, TopicName
from presentation.middleware.auth_jwt import get_service_principal
from presentation.schema.event_schemas import (
    BatchPublishRequest,
    BatchPublishResponse,
    EventPreviewResponse,
    PublishEventRequest,
    PublishEventResponse,
    ReplayEventRequest,
    ReplayEventResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])
security = HTTPBearer()


# FastAPI dependency functions
async def get_publish_use_case(request: Request) -> PublishEvent:
    """Get publish event use case from app state"""
    producer = request.app.state.kafka_producer
    event_store = request.app.state.redis_event_store
    return PublishEvent(producer=producer, event_store=event_store)


async def get_replay_use_case(request: Request) -> ReplayEvents:
    """Get replay events use case from app state"""
    producer = request.app.state.kafka_producer
    consumer = request.app.state.kafka_consumer
    event_store = request.app.state.redis_event_store

    if event_store is None:
        raise ValueError("Event store is required for replay functionality")

    return ReplayEvents(event_store=event_store, producer=producer, consumer=consumer)


@router.post("/publish", response_model=PublishEventResponse)
async def publish_event(
    request: PublishEventRequest,
    service: Principal = Depends(get_service_principal),
    publish_use_case: PublishEvent = Depends(get_publish_use_case),
):
    """Publish single domain event (service-to-service only)"""
    try:
        # Create domain event
        event = Event.create(
            event_type=request.event_type,
            payload=request.payload,
            user_id=request.user_id,  # User ID should be provided in request for service calls
            correlation_id=request.correlation_id,
            trace_id=request.trace_id,
            source=request.source or service.sub,  # Use service name as source
        )

        # Log event publishing
        logger.info(
            "Publishing event",
            event_id=event.event_id,
            event_type=event.event_type,
            user_id=event.user_id,
            source=event.source,
            service=service.sub,
        )

        # Publish event using Kafka
        published_event = await publish_use_case.execute(
            event_type=EventType(event.event_type),
            payload=event.payload,
            user_id=event.user_id,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
            source=event.source,
        )

        logger.info(
            "Event published successfully", event_id=event.event_id, event_type=event.event_type
        )

        return PublishEventResponse(
            event_id=published_event.event_id,
            event_type=published_event.event_type,
            timestamp=published_event.timestamp,
            status="published",
        )

    except ValueError as e:
        logger.warning("Event validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Event validation failed: {str(e)}") from None
    except Exception as e:
        logger.error("Event publish failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {str(e)}") from None


@router.post("/publish/batch", response_model=BatchPublishResponse)
async def publish_batch_events(
    request: BatchPublishRequest,
    service: Principal = Depends(get_service_principal),
    publish_use_case: PublishEvent = Depends(get_publish_use_case),
):
    """Publish multiple events in batch (service-to-service only)"""
    try:
        # Create events data from request
        events_data = []
        for event_data in request.events:
            events_data.append(
                {
                    "event_type": event_data.event_type,
                    "payload": event_data.payload,
                    "user_id": event_data.user_id,
                    "correlation_id": event_data.correlation_id,
                    "trace_id": event_data.trace_id,
                    "source": event_data.source or service.sub,
                }
            )

        # Publish batch
        published_events = await publish_use_case.execute_batch(events_data)

        return BatchPublishResponse(
            published_count=len(published_events),
            events=[
                PublishEventResponse(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    status="published",
                )
                for event in published_events
            ],
        )

    except EventValidationError as e:
        raise HTTPException(
            status_code=400, detail=f"Batch validation failed: {e.validation_errors}"
        ) from None
    except EventPublishError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to publish batch: {e.reason}"
        ) from None


@router.post("/replay", response_model=ReplayEventResponse)
async def replay_events(
    request: ReplayEventRequest,
    service: Principal = Depends(get_service_principal),
    replay_use_case: ReplayEvents = Depends(get_replay_use_case),
):
    """Replay events from event store (service-to-service only)"""
    try:
        event_types = None
        if request.event_types:
            event_types = [EventType(et) for et in request.event_types]

        target_topic = None
        if request.target_topic:
            target_topic = TopicName(request.target_topic)

        events = await replay_use_case.execute(
            from_timestamp=request.from_timestamp,
            to_timestamp=request.to_timestamp,
            event_types=event_types,
            user_id=request.user_id,
            target_topic=target_topic,
            dry_run=request.dry_run,
        )

        return ReplayEventResponse(
            replayed_count=len(events),
            from_timestamp=request.from_timestamp,
            to_timestamp=request.to_timestamp,
            dry_run=request.dry_run,
            events=[
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": event.user_id,
                }
                for event in events[:10]  # Return first 10 for preview
            ],
        )

    except EventReplayError as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {e.reason}") from None


@router.post("/replay/dlq", response_model=dict)
async def replay_dlq_events(
    dlq_topic: str = Query(default="dlq-events"),
    target_topic: str | None = Query(default=None),
    max_events: int = Query(default=100, ge=1, le=1000),
    service: Principal = Depends(get_service_principal),
    replay_use_case: ReplayEvents = Depends(get_replay_use_case),
):
    """Replay events from Dead Letter Queue (service-to-service only)"""
    try:
        dlq_topic_enum = TopicName(dlq_topic)
        target_topic_enum = TopicName(target_topic) if target_topic else None

        replayed_count = await replay_use_case.replay_dlq_events(
            dlq_topic=dlq_topic_enum, target_topic=target_topic_enum, max_events=max_events
        )

        return {
            "replayed_count": replayed_count,
            "dlq_topic": dlq_topic,
            "target_topic": target_topic,
            "max_events": max_events,
        }

    except EventReplayError as e:
        raise HTTPException(status_code=500, detail=f"DLQ replay failed: {e.reason}") from None


@router.get("/replay/preview", response_model=EventPreviewResponse)
async def get_replay_preview(
    from_timestamp: datetime = Query(...),
    to_timestamp: datetime = Query(...),
    event_types: list[str] | None = Query(default=None),
    user_id: str | None = Query(default=None),
    service: Principal = Depends(get_service_principal),
    replay_use_case: ReplayEvents = Depends(get_replay_use_case),
):
    """Get preview of events that would be replayed (service-to-service only)"""
    try:
        event_types_enum = None
        if event_types:
            event_types_enum = [EventType(et) for et in event_types]

        preview = await replay_use_case.get_replay_preview(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            event_types=event_types_enum,
            user_id=user_id,
        )

        return EventPreviewResponse(**preview)

    except EventReplayError as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {e.reason}") from None


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "events-service"}
