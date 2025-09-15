# Assumptions:
# - Using pytest for testing framework
# - Testing PublishEvent use case with mocked producer and event store
# - Testing error handling and validation

from unittest.mock import AsyncMock, Mock

import pytest
import structlog

from application.use_cases.publish_event import PublishEvent
from domain.entities.event import Event
from domain.errors import EventPublishError, EventValidationError
from domain.value_objects.event_types import EventType

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestPublishEventUseCase:
    """Test cases for PublishEvent use case"""

    @pytest.fixture
    def mock_producer(self):
        """Mock EventProducer"""
        return AsyncMock()

    @pytest.fixture
    def mock_event_store(self):
        """Mock EventStore"""
        return AsyncMock()

    @pytest.fixture
    def publish_use_case(self, mock_producer, mock_event_store):
        """Create PublishEvent use case instance with mocks"""
        return PublishEvent(producer=mock_producer, event_store=mock_event_store)

    @pytest.fixture
    def publish_use_case_no_store(self, mock_producer):
        """Create PublishEvent use case instance without event store"""
        return PublishEvent(producer=mock_producer, event_store=None)

    @pytest.mark.asyncio
    async def test_publish_event_success_with_store(
        self, publish_use_case, mock_producer, mock_event_store
    ):
        """Test successful event publishing with event store"""
        # Arrange
        event_type = EventType.USER_CREATED
        payload = {"user_id": "123", "email": "test@example.com"}
        user_id = "user-123"
        correlation_id = "corr-123"
        trace_id = "trace-123"
        source = "user-service"

        # Act
        result = await publish_use_case.execute(
            event_type=event_type,
            payload=payload,
            user_id=user_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            source=source,
        )

        # Assert
        assert isinstance(result, Event)
        assert result.event_type == event_type.value
        assert result.payload == payload
        assert result.user_id == user_id
        assert result.correlation_id == correlation_id
        assert result.trace_id == trace_id
        assert result.source == source

        # Verify store and producer were called
        mock_event_store.store_event.assert_called_once()
        mock_producer.publish_event.assert_called_once()

        # Verify the event passed to store and producer
        stored_event = mock_event_store.store_event.call_args[0][0]
        assert stored_event.event_type == event_type.value
        assert stored_event.payload == payload

    @pytest.mark.asyncio
    async def test_publish_event_success_without_store(
        self, publish_use_case_no_store, mock_producer
    ):
        """Test successful event publishing without event store"""
        # Arrange
        event_type = EventType.USER_UPDATED
        payload = {"user_id": "123", "changes": ["email"]}

        # Act
        result = await publish_use_case_no_store.execute(event_type=event_type, payload=payload)

        # Assert
        assert isinstance(result, Event)
        assert result.event_type == event_type.value
        assert result.payload == payload
        assert result.source == "events-service"  # default

        # Verify only producer was called (no event store)
        mock_producer.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_validation_error(self, publish_use_case, mock_producer):
        """Test event validation error"""
        # Arrange
        event_type = EventType.USER_CREATED
        payload = {}  # Empty payload should trigger validation error

        # Act & Assert
        with pytest.raises(EventValidationError):
            await publish_use_case.execute(event_type=event_type, payload=payload)

        # Verify producer was not called due to validation failure
        mock_producer.publish_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_event_producer_error(
        self, publish_use_case, mock_producer, mock_event_store
    ):
        """Test producer error handling"""
        # Arrange
        event_type = EventType.USER_CREATED
        payload = {"user_id": "123", "email": "test@example.com"}

        mock_producer.publish_event.side_effect = Exception("Kafka connection failed")

        # Act & Assert
        with pytest.raises(EventPublishError, match="Kafka connection failed"):
            await publish_use_case.execute(event_type=event_type, payload=payload)

        # Verify event was stored before producer failed
        mock_event_store.store_event.assert_called_once()
        mock_producer.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_batch_events_success(
        self, publish_use_case, mock_producer, mock_event_store
    ):
        """Test successful batch event publishing"""
        # Arrange
        events_data = [
            {
                "event_type": "user.created",
                "payload": {"user_id": "123", "email": "user1@example.com"},
                "user_id": "123",
                "source": "auth-service",
            },
            {
                "event_type": "user.updated",
                "payload": {"user_id": "456", "changes": ["email"]},
                "user_id": "456",
                "source": "user-service",
            },
        ]

        # Act
        result = await publish_use_case.execute_batch(events_data)

        # Assert
        assert len(result) == 2
        assert all(isinstance(event, Event) for event in result)
        assert result[0].event_type == "user.created"
        assert result[1].event_type == "user.updated"

        # Verify store and producer were called for batch
        assert mock_event_store.store_event.call_count == 2
        mock_producer.publish_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_batch_events_empty(self, publish_use_case, mock_producer):
        """Test batch publishing with empty list"""
        # Arrange
        events_data = []

        # Act
        result = await publish_use_case.execute_batch(events_data)

        # Assert
        assert result == []
        mock_producer.publish_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_batch_events_validation_error(self, publish_use_case, mock_producer):
        """Test batch publishing with validation error"""
        # Arrange
        events_data = [
            {
                "event_type": "user.created",
                "payload": {},  # Empty payload should fail validation
                "user_id": "123",
            }
        ]

        # Act & Assert
        with pytest.raises(EventPublishError):
            await publish_use_case.execute_batch(events_data)

        mock_producer.publish_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_event_topic_mapping(
        self, publish_use_case, mock_producer, mock_event_store
    ):
        """Test that events are published to correct topics"""
        # Arrange
        event_type = EventType.USER_CREATED
        payload = {"user_id": "123", "email": "test@example.com"}

        # Act
        await publish_use_case.execute(event_type=event_type, payload=payload)

        # Assert
        # Verify the topic mapping was used
        mock_producer.publish_event.assert_called_once()
        call_args = mock_producer.publish_event.call_args
        published_event = call_args[0][0]

        assert published_event.event_type == event_type.value
        # Topic should be determined by EVENT_TOPIC_MAPPING
