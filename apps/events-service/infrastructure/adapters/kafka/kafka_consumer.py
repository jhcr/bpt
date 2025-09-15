# Assumptions:
# - Kafka consumer using aiokafka library
# - Support for consumer groups and offset management
# - Event deserialization from JSON
# - Callback-based message handling

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer
from framework.config.env import get_env

from application.ports.event_consumer import EventConsumer
from domain.entities.event import Event
from domain.value_objects.event_types import TopicName

logger = structlog.get_logger(__name__)


class KafkaEventConsumer(EventConsumer):
    """Kafka implementation of EventConsumer port"""

    def __init__(self):
        self.bootstrap_servers = get_env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.consumers: dict[str, AIOKafkaConsumer] = {}
        self.consumer_tasks: dict[str, asyncio.Task] = {}

    async def start_consuming(
        self,
        topic: TopicName,
        handler: Callable[[Event], None],
        consumer_group: str,
        auto_commit: bool = True,
    ) -> None:
        """Start consuming events from topic"""
        consumer_key = f"{topic.value}-{consumer_group}"

        if consumer_key in self.consumers:
            logger.warning(
                "Consumer already running", topic=topic.value, consumer_group=consumer_group
            )
            return

        try:
            consumer = AIOKafkaConsumer(
                topic.value,
                bootstrap_servers=self.bootstrap_servers,
                group_id=consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=auto_commit,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                key_deserializer=lambda x: x.decode("utf-8") if x else None,
            )

            await consumer.start()
            self.consumers[consumer_key] = consumer

            # Start consuming task
            task = asyncio.create_task(
                self._consume_messages(consumer, handler, topic, consumer_group)
            )
            self.consumer_tasks[consumer_key] = task

            logger.info("Started consuming", topic=topic.value, consumer_group=consumer_group)

        except Exception as e:
            logger.error(
                "Failed to start consumer",
                topic=topic.value,
                consumer_group=consumer_group,
                error=str(e),
            )
            raise

    async def stop_consuming(self, topic: TopicName) -> None:
        """Stop consuming from topic"""
        consumers_to_stop = [
            key for key in self.consumers.keys() if key.startswith(f"{topic.value}-")
        ]

        for consumer_key in consumers_to_stop:
            try:
                # Cancel task
                if consumer_key in self.consumer_tasks:
                    task = self.consumer_tasks.pop(consumer_key)
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Stop consumer
                if consumer_key in self.consumers:
                    consumer = self.consumers.pop(consumer_key)
                    await consumer.stop()

                logger.info("Stopped consumer", consumer_key=consumer_key)

            except Exception as e:
                logger.error("Error stopping consumer", consumer_key=consumer_key, error=str(e))

    async def commit_offset(self, event: Event) -> None:
        """Manually commit offset for processed event"""
        # Note: This is a simplified implementation
        # In practice, you'd need to track partition/offset info
        for consumer in self.consumers.values():
            try:
                await consumer.commit()
                logger.debug("Committed offset", event_id=event.event_id)
            except Exception as e:
                logger.warning("Failed to commit offset", event_id=event.event_id, error=str(e))

    async def seek_to_timestamp(self, topic: TopicName, timestamp: datetime) -> None:
        """Seek consumer to specific timestamp"""
        consumers_for_topic = [
            consumer
            for key, consumer in self.consumers.items()
            if key.startswith(f"{topic.value}-")
        ]

        for consumer in consumers_for_topic:
            try:
                # Get topic partitions
                partitions = consumer.assignment()
                if not partitions:
                    logger.warning("No partitions assigned", topic=topic.value)
                    continue

                # Seek to timestamp
                timestamp_ms = int(timestamp.timestamp() * 1000)
                for partition in partitions:
                    consumer.seek_to_timestamp(partition, timestamp_ms)

                logger.info(
                    "Seeked to timestamp", topic=topic.value, timestamp=timestamp.isoformat()
                )

            except Exception as e:
                logger.error(
                    "Failed to seek to timestamp",
                    topic=topic.value,
                    timestamp=timestamp.isoformat(),
                    error=str(e),
                )

    async def get_consumer_lag(self, topic: TopicName, consumer_group: str) -> dict[str, int]:
        """Get consumer lag metrics"""
        consumer_key = f"{topic.value}-{consumer_group}"

        if consumer_key not in self.consumers:
            return {}

        try:
            consumer = self.consumers[consumer_key]

            # Get assigned partitions
            partitions = consumer.assignment()
            if not partitions:
                return {}

            # Get current offsets
            lag_info = {}
            for partition in partitions:
                try:
                    # Get current position
                    current_offset = await consumer.position(partition)

                    # Get high water mark (latest offset)
                    high_water_mark = await consumer.highwater(partition)

                    lag = high_water_mark - current_offset
                    lag_info[f"partition-{partition.partition}"] = lag

                except Exception as e:
                    logger.warning(
                        "Failed to get lag for partition",
                        partition=partition.partition,
                        error=str(e),
                    )
                    lag_info[f"partition-{partition.partition}"] = -1

            return lag_info

        except Exception as e:
            logger.error(
                "Failed to get consumer lag",
                topic=topic.value,
                consumer_group=consumer_group,
                error=str(e),
            )
            return {}

    async def _consume_messages(
        self,
        consumer: AIOKafkaConsumer,
        handler: Callable[[Event], None],
        topic: TopicName,
        consumer_group: str,
    ) -> None:
        """Internal method to consume messages"""
        try:
            async for message in consumer:
                try:
                    # Deserialize event
                    event_data = message.value
                    event = self._deserialize_event(event_data)

                    logger.debug(
                        "Received event",
                        event_id=event.event_id,
                        topic=topic.value,
                        partition=message.partition,
                        offset=message.offset,
                    )

                    # Call handler
                    handler(event)

                except Exception as e:
                    logger.error(
                        "Error processing message",
                        topic=topic.value,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            logger.info("Consumer task cancelled", topic=topic.value, consumer_group=consumer_group)
            raise
        except Exception as e:
            logger.error(
                "Consumer error", topic=topic.value, consumer_group=consumer_group, error=str(e)
            )

    def _deserialize_event(self, event_data: dict[str, Any]) -> Event:
        """Deserialize event data to Event entity"""
        return Event(
            event_id=event_data["event_id"],
            event_type=event_data["event_type"],
            user_id=event_data.get("user_id"),
            timestamp=datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00")),
            payload=event_data["payload"],
            metadata=event_data["metadata"],
            source=event_data.get("source", "unknown"),
            correlation_id=event_data.get("correlation_id"),
            trace_id=event_data.get("trace_id"),
        )

    async def shutdown(self) -> None:
        """Shutdown all consumers"""
        logger.info("Shutting down all consumers")

        # Cancel all tasks
        for task in self.consumer_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks.values(), return_exceptions=True)

        # Stop all consumers
        for consumer in self.consumers.values():
            try:
                await consumer.stop()
            except Exception as e:
                logger.warning("Error stopping consumer", error=str(e))

        self.consumers.clear()
        self.consumer_tasks.clear()

        logger.info("All consumers shutdown")
