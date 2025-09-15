# Assumptions:
# - Using pytest for testing framework
# - Testing Kafka producer with mocked aiokafka
# - Testing error handling and DLQ functionality

from datetime import UTC
from unittest.mock import AsyncMock, Mock, patch

import pytest
import structlog

from domain.entities.event import Event
from domain.errors import EventPublishError
from domain.value_objects.event_types import TopicName
from infrastructure.adapters.kafka.kafka_producer import KafkaEventProducer

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestKafkaEventProducer:
    """Test cases for Kafka event producer"""

    @pytest.fixture
    def mock_aiokafka_producer(self):
        """Mock AIOKafkaProducer"""
        return AsyncMock()

    @pytest.fixture
    def producer(self):
        """Create KafkaEventProducer instance"""
        with patch("infrastructure.adapters.kafka.kafka_producer.get_env") as mock_get_env:
            mock_get_env.return_value = "localhost:9092"
            return KafkaEventProducer()

    @pytest.fixture
    def sample_event(self):
        """Sample event for testing"""
        from datetime import datetime

        return Event(
            event_id="event-123",
            event_type="user.created",
            user_id="user-456",
            timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            payload={"email": "test@example.com", "name": "Test User"},
            metadata={"version": 1, "source": "auth-service"},
            source="auth-service",
            correlation_id="corr-123",
            trace_id="trace-456",
        )

    @pytest.mark.asyncio
    async def test_start_producer_success(self, producer):
        """Test successful producer startup"""
        with patch(
            "infrastructure.adapters.kafka.kafka_producer.AIOKafkaProducer"
        ) as mock_producer_class:
            mock_producer_instance = AsyncMock()
            mock_producer_class.return_value = mock_producer_instance

            # Act
            await producer.start()

            # Assert
            assert producer._started is True
            assert producer.producer == mock_producer_instance
            mock_producer_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_producer_already_started(self, producer):
        """Test starting producer when already started"""
        producer._started = True

        # Act
        await producer.start()

        # Assert - should not create new producer
        assert producer._started is True

    @pytest.mark.asyncio
    async def test_start_producer_failure(self, producer):
        """Test producer startup failure"""
        with patch(
            "infrastructure.adapters.kafka.kafka_producer.AIOKafkaProducer"
        ) as mock_producer_class:
            mock_producer_instance = AsyncMock()
            mock_producer_instance.start.side_effect = Exception("Connection failed")
            mock_producer_class.return_value = mock_producer_instance

            # Act & Assert
            with pytest.raises(EventPublishError, match="Producer startup failed"):
                await producer.start()

    @pytest.mark.asyncio
    async def test_stop_producer(self, producer):
        """Test producer shutdown"""
        mock_producer_instance = AsyncMock()
        producer.producer = mock_producer_instance
        producer._started = True

        # Act
        await producer.stop()

        # Assert
        assert producer._started is False
        mock_producer_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_success(self, producer, sample_event):
        """Test successful event publishing"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_future = AsyncMock()
        mock_record_metadata = Mock()
        mock_record_metadata.partition = 0
        mock_record_metadata.offset = 123
        mock_future.return_value = mock_record_metadata

        mock_producer_instance.send.return_value = mock_future
        producer.producer = mock_producer_instance
        producer._started = True

        target_topic = TopicName.USER_EVENTS

        # Act
        await producer.publish_event(sample_event, target_topic)

        # Assert
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args

        # Verify topic
        assert call_args[0][0] == target_topic.value

        # Verify serialized event data
        event_data = call_args[1]["value"]
        assert event_data["event_id"] == sample_event.event_id
        assert event_data["event_type"] == sample_event.event_type
        assert event_data["user_id"] == sample_event.user_id
        assert event_data["payload"] == sample_event.payload

        # Verify key is event_id
        assert call_args[1]["key"] == sample_event.event_id

    @pytest.mark.asyncio
    async def test_publish_event_auto_start(self, producer, sample_event):
        """Test event publishing auto-starts producer"""
        with patch.object(producer, "start") as mock_start:
            mock_producer_instance = AsyncMock()
            mock_future = AsyncMock()
            mock_future.return_value = Mock()
            mock_producer_instance.send.return_value = mock_future

            producer.producer = mock_producer_instance
            producer._started = False

            # Act
            await producer.publish_event(sample_event)

            # Assert
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_kafka_error(self, producer, sample_event):
        """Test Kafka error during publishing"""
        from aiokafka.errors import KafkaError

        # Arrange
        mock_producer_instance = AsyncMock()
        mock_producer_instance.send.side_effect = KafkaError("Broker not available")
        producer.producer = mock_producer_instance
        producer._started = True

        # Mock DLQ send to avoid actual publish
        with patch.object(producer, "_send_to_dlq", new_callable=AsyncMock) as mock_dlq:
            # Act & Assert
            with pytest.raises(EventPublishError, match="Kafka publish failed"):
                await producer.publish_event(sample_event)

            # Verify DLQ was called
            mock_dlq.assert_called_once_with(sample_event, "Broker not available")

    @pytest.mark.asyncio
    async def test_publish_event_default_topic_mapping(self, producer, sample_event):
        """Test publishing with default topic mapping"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_future = AsyncMock()
        mock_future.return_value = Mock()
        mock_producer_instance.send.return_value = mock_future
        producer.producer = mock_producer_instance
        producer._started = True

        # Act - publish without specifying topic
        await producer.publish_event(sample_event)

        # Assert - should use topic mapping
        mock_producer_instance.send.assert_called_once()
        # Topic should be determined by EVENT_TOPIC_MAPPING for the event type

    @pytest.mark.asyncio
    async def test_publish_events_batch_success(self, producer, sample_event):
        """Test successful batch event publishing"""
        # Arrange
        events = [sample_event, sample_event]  # Duplicate for simplicity
        mock_producer_instance = AsyncMock()
        mock_future = AsyncMock()
        mock_future.return_value = Mock()
        mock_producer_instance.send.return_value = mock_future
        producer.producer = mock_producer_instance
        producer._started = True

        # Act
        await producer.publish_events(events)

        # Assert
        assert mock_producer_instance.send.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_events_batch_partial_failure(self, producer, sample_event):
        """Test batch publishing with some failures"""
        # Arrange
        events = [sample_event, sample_event]
        mock_producer_instance = AsyncMock()

        # First future succeeds, second fails
        mock_future_success = AsyncMock()
        mock_future_success.return_value = Mock()
        mock_future_fail = AsyncMock()
        mock_future_fail.side_effect = Exception("Send failed")

        mock_producer_instance.send.side_effect = [mock_future_success, mock_future_fail]
        producer.producer = mock_producer_instance
        producer._started = True

        # Mock DLQ send
        with patch.object(producer, "_send_to_dlq", new_callable=AsyncMock) as mock_dlq:
            # Act
            await producer.publish_events(events)

            # Assert
            assert mock_producer_instance.send.call_count == 2
            # Failed event should be sent to DLQ
            mock_dlq.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, producer):
        """Test health check when producer is healthy"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.brokers = ["broker1", "broker2"]
        mock_producer_instance.client.fetch_metadata.return_value = mock_metadata
        producer.producer = mock_producer_instance
        producer._started = True

        # Act
        result = await producer.health_check()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_not_started(self, producer):
        """Test health check when producer not started"""
        # Arrange
        producer._started = False

        # Act
        result = await producer.health_check()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_no_brokers(self, producer):
        """Test health check when no brokers available"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_metadata = Mock()
        mock_metadata.brokers = []
        mock_producer_instance.client.fetch_metadata.return_value = mock_metadata
        producer.producer = mock_producer_instance
        producer._started = True

        # Act
        result = await producer.health_check()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_dlq_success(self, producer, sample_event):
        """Test successful DLQ send"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_future = AsyncMock()
        mock_future.return_value = Mock()
        mock_producer_instance.send.return_value = mock_future
        producer.producer = mock_producer_instance

        error_reason = "Original publish failed"

        # Act
        await producer._send_to_dlq(sample_event, error_reason)

        # Assert
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args

        # Verify DLQ topic
        assert call_args[0][0] == TopicName.DLQ_EVENTS.value

        # Verify DLQ data structure
        dlq_data = call_args[1]["value"]
        assert "original_event" in dlq_data
        assert dlq_data["failure_reason"] == error_reason
        assert "failure_timestamp" in dlq_data

    @pytest.mark.asyncio
    async def test_send_to_dlq_failure(self, producer, sample_event):
        """Test DLQ send failure (should not raise)"""
        # Arrange
        mock_producer_instance = AsyncMock()
        mock_producer_instance.send.side_effect = Exception("DLQ send failed")
        producer.producer = mock_producer_instance

        # Act - should not raise exception
        await producer._send_to_dlq(sample_event, "Original error")

        # Assert - should log error but not raise
