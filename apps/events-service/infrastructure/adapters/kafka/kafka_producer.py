# Assumptions:
# - Kafka producer using aiokafka library
# - JSON serialization for events
# - Error handling and retry logic
# - Dead letter queue support

import json

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from framework.config.env import get_env

from application.ports.event_producer import EventProducer
from domain.entities.event import Event
from domain.errors import EventPublishError
from domain.value_objects.event_types import EVENT_TOPIC_MAPPING, TopicName

logger = structlog.get_logger(__name__)


class KafkaEventProducer(EventProducer):
    """Kafka implementation of EventProducer port"""

    def __init__(self):
        self.bootstrap_servers = get_env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.producer: AIOKafkaProducer | None = None
        self._started = False

    async def start(self) -> None:
        """Start Kafka producer"""
        if self._started:
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                key_serializer=lambda x: x.encode("utf-8") if x else None,
                # Kafka producer config
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=5,
                enable_idempotence=True,
                batch_size=16384,
                linger_ms=5,
            )

            await self.producer.start()
            self._started = True

            logger.info("Kafka producer started", bootstrap_servers=self.bootstrap_servers)

        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise EventPublishError("", "", f"Producer startup failed: {str(e)}") from e

    async def stop(self) -> None:
        """Stop Kafka producer"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def publish_event(self, event: Event, topic: TopicName | None = None) -> None:
        """Publish single event to Kafka"""
        if not self._started:
            await self.start()

        try:
            # Determine topic
            if topic is None:
                from ....domain.value_objects.event_types import EventType

                event_type = EventType(event.event_type)
                topic = EVENT_TOPIC_MAPPING.get(event_type, TopicName.SYSTEM_EVENTS)

            # Serialize event
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload,
                "metadata": event.metadata,
                "source": event.source,
                "correlation_id": event.correlation_id,
                "trace_id": event.trace_id,
            }

            # Use event_id as key for partitioning
            key = event.event_id

            # Send to Kafka
            future = await self.producer.send(topic.value, value=event_data, key=key)

            # Wait for confirmation
            record_metadata = await future

            logger.debug(
                "Event published to Kafka",
                event_id=event.event_id,
                topic=topic.value,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
            )

        except KafkaError as e:
            logger.error(
                "Kafka publish error",
                event_id=event.event_id,
                topic=topic.value if topic else "unknown",
                error=str(e),
            )

            # Try to send to DLQ
            await self._send_to_dlq(event, str(e))

            raise EventPublishError(
                event_id=event.event_id,
                event_type=event.event_type,
                reason=f"Kafka publish failed: {str(e)}",
            ) from e

        except Exception as e:
            logger.error("Unexpected publish error", event_id=event.event_id, error=str(e))
            raise EventPublishError(
                event_id=event.event_id,
                event_type=event.event_type,
                reason=f"Publish failed: {str(e)}",
            ) from e

    async def publish_events(self, events: list[Event], topic: TopicName | None = None) -> None:
        """Publish multiple events in batch"""
        if not self._started:
            await self.start()

        try:
            # Send all events
            futures = []
            for event in events:
                event_topic = topic
                if event_topic is None:
                    from ....domain.value_objects.event_types import EventType

                    event_type = EventType(event.event_type)
                    event_topic = EVENT_TOPIC_MAPPING.get(event_type, TopicName.SYSTEM_EVENTS)

                event_data = {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload,
                    "metadata": event.metadata,
                    "source": event.source,
                    "correlation_id": event.correlation_id,
                    "trace_id": event.trace_id,
                }

                future = await self.producer.send(
                    event_topic.value, value=event_data, key=event.event_id
                )
                futures.append((event, future))

            # Wait for all confirmations
            failed_events = []
            for event, future in futures:
                try:
                    await future
                except Exception as e:
                    logger.warning("Batch event failed", event_id=event.event_id, error=str(e))
                    failed_events.append(event)

            if failed_events:
                logger.warning(
                    "Some batch events failed",
                    failed_count=len(failed_events),
                    total_count=len(events),
                )

                # Send failed events to DLQ
                for event in failed_events:
                    await self._send_to_dlq(event, "Batch publish failed")

            logger.info(
                "Batch publish completed",
                total_events=len(events),
                failed_events=len(failed_events),
            )

        except Exception as e:
            logger.error("Batch publish error", error=str(e))
            raise EventPublishError(
                event_id="batch", event_type="batch", reason=f"Batch publish failed: {str(e)}"
            ) from e

    async def health_check(self) -> bool:
        """Check if producer is healthy"""
        try:
            if not self._started:
                return False

            # Try to get cluster metadata
            metadata = await self.producer.client.fetch_metadata()
            return len(metadata.brokers) > 0

        except Exception as e:
            logger.warning("Producer health check failed", error=str(e))
            return False

    async def _send_to_dlq(self, event: Event, error_reason: str) -> None:
        """Send failed event to Dead Letter Queue"""
        try:
            dlq_data = {
                "original_event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload,
                    "metadata": event.metadata,
                    "source": event.source,
                    "correlation_id": event.correlation_id,
                    "trace_id": event.trace_id,
                },
                "failure_reason": error_reason,
                "failure_timestamp": event.timestamp.isoformat(),
                "retry_count": event.metadata.get("retry_count", 0),
            }

            await self.producer.send(TopicName.DLQ_EVENTS.value, value=dlq_data, key=event.event_id)

            logger.info("Event sent to DLQ", event_id=event.event_id, reason=error_reason)

        except Exception as dlq_error:
            logger.error(
                "Failed to send event to DLQ",
                event_id=event.event_id,
                original_error=error_reason,
                dlq_error=str(dlq_error),
            )
