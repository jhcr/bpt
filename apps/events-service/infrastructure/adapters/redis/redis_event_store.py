# Assumptions:
# - Redis as event store for replay functionality
# - JSON serialization for events
# - Time-based indexing for queries
# - Optional implementation (Kafka can also serve as event store)

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis
import structlog
from framework.config.env import get_env

from application.ports.event_store import EventStore
from domain.entities.event import Event
from domain.value_objects.event_types import EventType

logger = structlog.get_logger(__name__)


class RedisEventStore(EventStore):
    """Redis implementation of EventStore port"""

    def __init__(self):
        self.redis_url = get_env("REDIS_URL", "redis://localhost:6379")
        self.redis: redis.Redis | None = None
        self.key_prefix = "events"
        self.index_prefix = "events:index"

    async def connect(self) -> None:
        """Connect to Redis"""
        if self.redis is None:
            try:
                self.redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )

                # Test connection
                await self.redis.ping()
                logger.info("Connected to Redis event store", url=self.redis_url)

            except Exception as e:
                logger.error("Failed to connect to Redis", error=str(e))
                raise

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis event store")

    async def store_event(self, event: Event) -> None:
        """Store event in Redis"""
        if not self.redis:
            await self.connect()

        try:
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

            # Store event data
            event_key = f"{self.key_prefix}:{event.event_id}"
            await self.redis.set(
                event_key,
                json.dumps(event_data),
                ex=86400 * 30,  # 30 days TTL
            )

            # Create time-based index
            timestamp_key = f"{self.index_prefix}:time:{event.timestamp.strftime('%Y-%m-%d')}"
            await self.redis.zadd(timestamp_key, {event.event_id: event.timestamp.timestamp()})
            await self.redis.expire(timestamp_key, 86400 * 31)  # 31 days TTL

            # Create user-based index if user_id exists
            if event.user_id:
                user_key = f"{self.index_prefix}:user:{event.user_id}"
                await self.redis.zadd(user_key, {event.event_id: event.timestamp.timestamp()})
                await self.redis.expire(user_key, 86400 * 31)

            # Create event type index
            type_key = f"{self.index_prefix}:type:{event.event_type}"
            await self.redis.zadd(type_key, {event.event_id: event.timestamp.timestamp()})
            await self.redis.expire(type_key, 86400 * 31)

            logger.debug("Event stored in Redis", event_id=event.event_id)

        except Exception as e:
            logger.error("Failed to store event in Redis", event_id=event.event_id, error=str(e))
            raise

    async def get_events_by_time_range(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
        user_id: str | None = None,
    ) -> list[Event]:
        """Get events within time range"""
        if not self.redis:
            await self.connect()

        try:
            # Get date range for index keys
            start_date = from_timestamp.date()
            end_date = to_timestamp.date()

            # Collect event IDs from time indexes
            event_ids = set()
            current_date = start_date

            while current_date <= end_date:
                time_key = f"{self.index_prefix}:time:{current_date.strftime('%Y-%m-%d')}"

                # Get events in timestamp range for this day
                day_event_ids = await self.redis.zrangebyscore(
                    time_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                )
                event_ids.update(day_event_ids)

                current_date = datetime(
                    current_date.year, current_date.month, current_date.day + 1
                ).date()

            # Filter by user_id if specified
            if user_id:
                user_key = f"{self.index_prefix}:user:{user_id}"
                user_event_ids = await self.redis.zrangebyscore(
                    user_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                )
                event_ids = event_ids.intersection(set(user_event_ids))

            # Filter by event_types if specified
            if event_types:
                type_event_ids = set()
                for event_type in event_types:
                    type_key = f"{self.index_prefix}:type:{event_type.value}"
                    type_ids = await self.redis.zrangebyscore(
                        type_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                    )
                    type_event_ids.update(type_ids)
                event_ids = event_ids.intersection(type_event_ids)

            # Retrieve event data
            events = []
            if event_ids:
                event_keys = [f"{self.key_prefix}:{event_id}" for event_id in event_ids]
                event_data_list = await self.redis.mget(event_keys)

                for event_data in event_data_list:
                    if event_data:
                        try:
                            data = json.loads(event_data)
                            event = self._deserialize_event(data)
                            events.append(event)
                        except Exception as e:
                            logger.warning(
                                "Failed to deserialize event",
                                event_data=event_data[:100],
                                error=str(e),
                            )

            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)

            logger.info(
                "Retrieved events from time range",
                count=len(events),
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
            )

            return events

        except Exception as e:
            logger.error(
                "Failed to get events by time range",
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
                error=str(e),
            )
            raise

    async def get_events_by_user(
        self,
        user_id: str,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get events for specific user"""
        if not self.redis:
            await self.connect()

        try:
            user_key = f"{self.index_prefix}:user:{user_id}"

            # Set time bounds
            min_score = from_timestamp.timestamp() if from_timestamp else "-inf"
            max_score = to_timestamp.timestamp() if to_timestamp else "+inf"

            # Get event IDs
            event_ids = await self.redis.zrevrangebyscore(
                user_key, max_score, min_score, start=0, num=limit
            )

            # Retrieve events
            events = []
            if event_ids:
                event_keys = [f"{self.key_prefix}:{event_id}" for event_id in event_ids]
                event_data_list = await self.redis.mget(event_keys)

                for event_data in event_data_list:
                    if event_data:
                        try:
                            data = json.loads(event_data)
                            event = self._deserialize_event(data)
                            events.append(event)
                        except Exception as e:
                            logger.warning("Failed to deserialize user event", error=str(e))

            return events

        except Exception as e:
            logger.error("Failed to get events by user", user_id=user_id, error=str(e))
            raise

    async def get_event_by_id(self, event_id: str) -> Event | None:
        """Get specific event by ID"""
        if not self.redis:
            await self.connect()

        try:
            event_key = f"{self.key_prefix}:{event_id}"
            event_data = await self.redis.get(event_key)

            if event_data:
                data = json.loads(event_data)
                return self._deserialize_event(data)

            return None

        except Exception as e:
            logger.error("Failed to get event by ID", event_id=event_id, error=str(e))
            raise

    async def count_events(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
    ) -> int:
        """Count events in time range"""
        if not self.redis:
            await self.connect()

        try:
            # Get date range for index keys
            start_date = from_timestamp.date()
            end_date = to_timestamp.date()

            # Count events from time indexes
            total_count = 0
            current_date = start_date

            while current_date <= end_date:
                time_key = f"{self.index_prefix}:time:{current_date.strftime('%Y-%m-%d')}"

                if event_types:
                    # If filtering by event types, need to intersect
                    day_event_ids = await self.redis.zrangebyscore(
                        time_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                    )

                    # Filter by event types
                    type_event_ids = set()
                    for event_type in event_types:
                        type_key = f"{self.index_prefix}:type:{event_type.value}"
                        type_ids = await self.redis.zrangebyscore(
                            type_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                        )
                        type_event_ids.update(type_ids)

                    # Count intersection
                    filtered_ids = set(day_event_ids).intersection(type_event_ids)
                    total_count += len(filtered_ids)
                else:
                    # Count all events in time range for this day
                    day_count = await self.redis.zcount(
                        time_key, from_timestamp.timestamp(), to_timestamp.timestamp()
                    )
                    total_count += day_count

                current_date = datetime(
                    current_date.year, current_date.month, current_date.day + 1
                ).date()

            return total_count

        except Exception as e:
            logger.error(
                "Failed to count events",
                from_timestamp=from_timestamp.isoformat(),
                to_timestamp=to_timestamp.isoformat(),
                error=str(e),
            )
            raise

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
