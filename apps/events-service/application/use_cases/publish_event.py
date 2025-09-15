# Assumptions:
# - Use case for publishing events with validation
# - Support for dead letter queue on failure
# - Automatic topic routing

from typing import Any

import structlog

from application.ports.event_producer import EventProducer
from application.ports.event_store import EventStore
from domain.entities.event import Event
from domain.errors import EventPublishError, EventValidationError
from domain.value_objects.event_types import EVENT_TOPIC_MAPPING, EventType, TopicName

logger = structlog.get_logger(__name__)


class PublishEvent:
    """Use case for publishing domain events"""

    def __init__(self, producer: EventProducer, event_store: EventStore | None = None):
        self.producer = producer
        self.event_store = event_store

    async def execute(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        user_id: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        source: str = "events-service",
    ) -> Event:
        """
        Publish domain event

        Args:
            event_type: Type of event
            payload: Event payload
            user_id: Optional user ID
            correlation_id: Optional correlation ID
            trace_id: Optional trace ID
            source: Event source service

        Returns:
            Published event

        Raises:
            EventValidationError: If event validation fails
            EventPublishError: If publishing fails
        """
        try:
            # Create event
            event = Event.create(
                event_type=event_type.value,
                payload=payload,
                user_id=user_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
                source=source,
            )

            # Validate event
            self._validate_event(event)

            # Determine topic
            topic = EVENT_TOPIC_MAPPING.get(event_type, TopicName.SYSTEM_EVENTS)

            logger.info(
                "Publishing event",
                event_id=event.event_id,
                event_type=event.event_type,
                topic=topic,
                user_id=user_id,
            )

            # Store event if event store is available
            if self.event_store:
                await self.event_store.store_event(event)

            # Publish to Kafka
            await self.producer.publish_event(event, topic)

            logger.info(
                "Event published successfully", event_id=event.event_id, event_type=event.event_type
            )

            return event

        except EventValidationError:
            logger.warning("Event validation failed", event_type=event_type, user_id=user_id)
            raise
        except Exception as e:
            logger.error(
                "Failed to publish event", event_type=event_type, user_id=user_id, error=str(e)
            )
            raise EventPublishError(
                event_id=event.event_id if "event" in locals() else "unknown",
                event_type=event_type.value,
                reason=str(e),
            ) from e

    async def execute_batch(self, events_data: list[dict[str, Any]]) -> list[Event]:
        """
        Publish multiple events in batch

        Args:
            events_data: List of event data dictionaries

        Returns:
            List of published events
        """
        try:
            events = []

            # Create all events
            for event_data in events_data:
                event = Event.create(
                    event_type=event_data["event_type"],
                    payload=event_data["payload"],
                    user_id=event_data.get("user_id"),
                    correlation_id=event_data.get("correlation_id"),
                    trace_id=event_data.get("trace_id"),
                    source=event_data.get("source", "events-service"),
                )

                # Validate each event
                self._validate_event(event)
                events.append(event)

            logger.info("Publishing batch of events", count=len(events))

            # Group events by topic
            events_by_topic = {}
            for event in events:
                event_type_enum = EventType(event.event_type)
                topic = EVENT_TOPIC_MAPPING.get(event_type_enum, TopicName.SYSTEM_EVENTS)

                if topic not in events_by_topic:
                    events_by_topic[topic] = []
                events_by_topic[topic].append(event)

            # Store events if event store is available
            if self.event_store:
                for event in events:
                    await self.event_store.store_event(event)

            # Publish by topic
            for topic, topic_events in events_by_topic.items():
                await self.producer.publish_events(topic_events, topic)

            logger.info("Batch events published successfully", count=len(events))

            return events

        except Exception as e:
            logger.error("Failed to publish batch events", error=str(e))
            raise EventPublishError(event_id="batch", event_type="batch", reason=str(e)) from e

    def _validate_event(self, event: Event) -> None:
        """Validate event before publishing"""
        errors = []

        # Basic validation
        if not event.event_id:
            errors.append("event_id is required")

        if not event.event_type:
            errors.append("event_type is required")

        if not event.payload:
            errors.append("payload cannot be empty")

        if not event.metadata:
            errors.append("metadata is required")

        # Event type validation
        try:
            EventType(event.event_type)
        except ValueError:
            errors.append(f"Invalid event_type: {event.event_type}")

        if errors:
            raise EventValidationError(
                event_id=event.event_id, event_type=event.event_type, validation_errors=errors
            )
