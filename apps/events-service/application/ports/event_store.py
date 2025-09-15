# Assumptions:
# - Abstract event store for replay and audit
# - Support for time-based queries
# - Optional implementation (can use Kafka as event store)

from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.event import Event
from domain.value_objects.event_types import EventType


class EventStore(ABC):
    """Abstract event store port for replay and auditing"""

    @abstractmethod
    async def store_event(self, event: Event) -> None:
        """Store event for replay purposes"""
        pass

    @abstractmethod
    async def get_events_by_time_range(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
        user_id: str | None = None,
    ) -> list[Event]:
        """Get events within time range"""
        pass

    @abstractmethod
    async def get_events_by_user(
        self,
        user_id: str,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get events for specific user"""
        pass

    @abstractmethod
    async def get_event_by_id(self, event_id: str) -> Event | None:
        """Get specific event by ID"""
        pass

    @abstractmethod
    async def count_events(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        event_types: list[EventType] | None = None,
    ) -> int:
        """Count events in time range"""
        pass
