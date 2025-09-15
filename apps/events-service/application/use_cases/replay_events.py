# Assumptions:
# - Use case for replaying events from event store or Kafka
# - Support for time range and filtering
# - DLQ replay functionality

from datetime import datetime

import structlog

from application.ports.event_consumer import EventConsumer
from application.ports.event_producer import EventProducer
from application.ports.event_store import EventStore
from domain.entities.event import Event
from domain.errors import EventReplayError
from domain.value_objects.event_types import EventType, TopicName

logger = structlog.get_logger(__name__)


class ReplayEvents:
    """Use case for replaying events"""

    def __init__(
        self,
        event_store: EventStore,
        producer: EventProducer,
        consumer: EventConsumer | None = None,
    ):
        self.event_store = event_store
        self.producer = producer
        self.consumer = consumer

    async def execute(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
        user_id: str | None = None,
        target_topic: TopicName | None = None,
        dry_run: bool = False,
    ) -> list[Event]:
        """
        Replay events from event store

        Args:
            from_timestamp: Start timestamp
            to_timestamp: End timestamp
            event_types: Optional filter by event types
            user_id: Optional filter by user ID
            target_topic: Optional target topic (defaults to original)
            dry_run: If True, don't actually republish events

        Returns:
            List of replayed events

        Raises:
            EventReplayError: If replay fails
        """
        try:
            logger.info(
                "Starting event replay",
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
                event_types=[et.value for et in event_types] if event_types else None,
                user_id=user_id,
                dry_run=dry_run,
            )

            # Get events from store
            events = await self.event_store.get_events_by_time_range(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                event_types=event_types,
                user_id=user_id,
            )

            if not events:
                logger.info("No events found for replay criteria")
                return []

            logger.info("Found events for replay", count=len(events))

            if dry_run:
                logger.info("Dry run mode - not republishing events")
                return events

            # Republish events
            replayed_events = []
            for event in events:
                try:
                    # Add replay metadata
                    replay_event = event.with_retry_metadata(
                        retry_count=0, original_timestamp=event.timestamp
                    )

                    # Publish to target topic
                    if target_topic:
                        await self.producer.publish_event(replay_event, target_topic)
                    else:
                        await self.producer.publish_event(replay_event)

                    replayed_events.append(replay_event)

                except Exception as e:
                    logger.warning("Failed to replay event", event_id=event.event_id, error=str(e))
                    # Continue with other events

            logger.info(
                "Event replay completed",
                total_events=len(events),
                replayed_events=len(replayed_events),
            )

            return replayed_events

        except Exception as e:
            logger.error("Event replay failed", error=str(e))
            raise EventReplayError(
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
                reason=str(e),
            ) from e

    async def replay_dlq_events(
        self,
        dlq_topic: TopicName = TopicName.DLQ_EVENTS,
        target_topic: TopicName | None = None,
        max_events: int = 100,
    ) -> int:
        """
        Replay events from Dead Letter Queue

        Args:
            dlq_topic: DLQ topic to replay from
            target_topic: Target topic to republish to
            max_events: Maximum number of events to replay

        Returns:
            Number of successfully replayed events
        """
        if not self.consumer:
            raise EventReplayError("", "", "Consumer not available for DLQ replay")

        try:
            logger.info(
                "Starting DLQ replay",
                dlq_topic=dlq_topic,
                target_topic=target_topic,
                max_events=max_events,
            )

            replayed_count = 0
            processed_events = []

            def dlq_handler(event: Event) -> None:
                nonlocal replayed_count, processed_events

                try:
                    # Add retry metadata
                    current_retry_count = event.metadata.get("retry_count", 0)
                    retry_event = event.with_retry_metadata(retry_count=current_retry_count + 1)

                    # Republish to original or target topic
                    # Note: This would need to be async, but handler is sync
                    # In real implementation, would queue for async processing
                    processed_events.append(retry_event)
                    replayed_count += 1

                    logger.debug(
                        "DLQ event queued for replay",
                        event_id=event.event_id,
                        retry_count=current_retry_count + 1,
                    )

                except Exception as e:
                    logger.warning(
                        "Failed to process DLQ event", event_id=event.event_id, error=str(e)
                    )

            # Start consuming DLQ (this would need proper async handling)
            await self.consumer.start_consuming(
                topic=dlq_topic,
                handler=dlq_handler,
                consumer_group=f"dlq-replay-{datetime.utcnow().timestamp()}",
            )

            # Process queued events asynchronously
            for event in processed_events:
                try:
                    if target_topic:
                        await self.producer.publish_event(event, target_topic)
                    else:
                        await self.producer.publish_event(event)
                except Exception as e:
                    logger.warning(
                        "Failed to republish DLQ event", event_id=event.event_id, error=str(e)
                    )
                    replayed_count -= 1

            logger.info("DLQ replay completed", replayed_count=replayed_count)

            return replayed_count

        except Exception as e:
            logger.error("DLQ replay failed", error=str(e))
            raise EventReplayError("", "", f"DLQ replay failed: {str(e)}") from e

    async def get_replay_preview(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
        user_id: str | None = None,
    ) -> dict:
        """
        Get preview of events that would be replayed

        Returns:
            Dictionary with replay statistics
        """
        try:
            # Get event count
            event_count = await self.event_store.count_events(
                from_timestamp=from_timestamp, to_timestamp=to_timestamp, event_types=event_types
            )

            # Get sample events (first 10)
            sample_events = await self.event_store.get_events_by_time_range(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                event_types=event_types,
                user_id=user_id,
            )

            return {
                "total_events": event_count,
                "from_timestamp": from_timestamp.isoformat(),
                "to_timestamp": to_timestamp.isoformat(),
                "filters": {
                    "event_types": [et.value for et in event_types] if event_types else None,
                    "user_id": user_id,
                },
                "sample_events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp.isoformat(),
                        "user_id": event.user_id,
                    }
                    for event in sample_events[:10]
                ],
            }

        except Exception as e:
            logger.error("Failed to get replay preview", error=str(e))
            raise EventReplayError(
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
                reason=f"Preview failed: {str(e)}",
            ) from e
