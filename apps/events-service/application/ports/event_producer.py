# Assumptions:
# - Abstract producer port for dependency inversion
# - Support for async operations
# - Error handling and retry logic

from abc import ABC, abstractmethod

from domain.entities.event import Event
from domain.value_objects.event_types import TopicName


class EventProducer(ABC):
    """Abstract event producer port"""

    @abstractmethod
    async def publish_event(self, event: Event, topic: TopicName | None = None) -> None:
        """
        Publish single event

        Args:
            event: Event to publish
            topic: Optional topic override

        Raises:
            EventPublishError: If publishing fails
        """
        pass

    @abstractmethod
    async def publish_events(self, events: list[Event], topic: TopicName | None = None) -> None:
        """
        Publish multiple events in batch

        Args:
            events: List of events to publish
            topic: Optional topic override

        Raises:
            EventPublishError: If publishing fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if producer is healthy

        Returns:
            True if healthy, False otherwise
        """
        pass
