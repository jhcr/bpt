# Assumptions:
# - Abstract consumer port for dependency inversion
# - Support for message acknowledgment and retry
# - Callback-based event handling

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

from domain.entities.event import Event
from domain.value_objects.event_types import TopicName


class EventConsumer(ABC):
    """Abstract event consumer port"""

    @abstractmethod
    async def start_consuming(
        self,
        topic: TopicName,
        handler: Callable[[Event], None],
        consumer_group: str,
        auto_commit: bool = True,
    ) -> None:
        """
        Start consuming events from topic

        Args:
            topic: Topic to consume from
            handler: Event handler function
            consumer_group: Consumer group ID
            auto_commit: Whether to auto-commit offsets
        """
        pass

    @abstractmethod
    async def stop_consuming(self, topic: TopicName) -> None:
        """Stop consuming from topic"""
        pass

    @abstractmethod
    async def commit_offset(self, event: Event) -> None:
        """Manually commit offset for processed event"""
        pass

    @abstractmethod
    async def seek_to_timestamp(self, topic: TopicName, timestamp: datetime) -> None:
        """Seek consumer to specific timestamp"""
        pass

    @abstractmethod
    async def get_consumer_lag(self, topic: TopicName, consumer_group: str) -> dict[str, int]:
        """Get consumer lag metrics"""
        pass
