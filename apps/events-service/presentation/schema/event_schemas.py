# Assumptions:
# - Pydantic schemas for request/response validation
# - Support for batch operations
# - Event replay request/response models

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class PublishEventRequest(BaseModel):
    """Request schema for publishing single event"""

    event_type: str = Field(..., description="Type of event to publish")
    payload: dict[str, Any] = Field(..., description="Event payload data")
    user_id: str | None = Field(None, description="User ID associated with the event")
    correlation_id: str | None = Field(None, description="Correlation ID for tracing")
    trace_id: str | None = Field(None, description="Trace ID for distributed tracing")
    source: str | None = Field(None, description="Source service name")

    @validator("event_type")
    def validate_event_type(cls, v):
        # Basic validation - actual validation happens in domain layer
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()

    @validator("payload")
    def validate_payload(cls, v):
        if not v:
            raise ValueError("payload cannot be empty")
        return v


class PublishEventResponse(BaseModel):
    """Response schema for published event"""

    event_id: str = Field(..., description="Generated event ID")
    event_type: str = Field(..., description="Type of published event")
    timestamp: datetime = Field(..., description="Event timestamp")
    status: str = Field(..., description="Publication status")


class BatchEventData(BaseModel):
    """Single event data for batch publishing"""

    event_type: str = Field(..., description="Type of event")
    payload: dict[str, Any] = Field(..., description="Event payload")
    user_id: str | None = Field(None, description="User ID associated with the event")
    correlation_id: str | None = Field(None, description="Correlation ID")
    trace_id: str | None = Field(None, description="Trace ID")
    source: str | None = Field("events-service", description="Source service")

    @validator("event_type")
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()

    @validator("payload")
    def validate_payload(cls, v):
        if not v:
            raise ValueError("payload cannot be empty")
        return v


class BatchPublishRequest(BaseModel):
    """Request schema for batch event publishing"""

    events: list[BatchEventData] = Field(..., description="List of events to publish")

    @validator("events")
    def validate_events_not_empty(cls, v):
        if not v:
            raise ValueError("events list cannot be empty")
        if len(v) > 100:  # Reasonable batch limit
            raise ValueError("batch size cannot exceed 100 events")
        return v


class BatchPublishResponse(BaseModel):
    """Response schema for batch event publishing"""

    published_count: int = Field(..., description="Number of successfully published events")
    events: list[PublishEventResponse] = Field(..., description="Details of published events")


class ReplayEventRequest(BaseModel):
    """Request schema for event replay"""

    from_timestamp: datetime = Field(..., description="Start timestamp for replay")
    to_timestamp: datetime = Field(..., description="End timestamp for replay")
    event_types: list[str] | None = Field(None, description="Filter by event types")
    user_id: str | None = Field(None, description="Filter by user ID")
    target_topic: str | None = Field(None, description="Target topic for replay")
    dry_run: bool = Field(False, description="Preview mode - don't actually replay")

    @validator("to_timestamp")
    def validate_timestamp_range(cls, v, values):
        if "from_timestamp" in values and v <= values["from_timestamp"]:
            raise ValueError("to_timestamp must be after from_timestamp")
        return v

    @validator("event_types")
    def validate_event_types(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("event_types cannot be empty list")
        return v


class EventSummary(BaseModel):
    """Summary of single event for replay response"""

    event_id: str
    event_type: str
    timestamp: str
    user_id: str | None


class ReplayEventResponse(BaseModel):
    """Response schema for event replay"""

    replayed_count: int = Field(..., description="Number of events replayed")
    from_timestamp: datetime = Field(..., description="Replay start timestamp")
    to_timestamp: datetime = Field(..., description="Replay end timestamp")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    events: list[dict[str, Any]] = Field(..., description="Sample of replayed events")


class EventPreviewResponse(BaseModel):
    """Response schema for replay preview"""

    total_events: int = Field(..., description="Total events in time range")
    from_timestamp: str = Field(..., description="Start timestamp")
    to_timestamp: str = Field(..., description="End timestamp")
    filters: dict[str, Any] = Field(..., description="Applied filters")
    sample_events: list[dict[str, Any]] = Field(..., description="Sample events")


class ErrorResponse(BaseModel):
    """Standard error response schema"""

    error: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
