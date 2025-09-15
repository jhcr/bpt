# Assumptions:
# - Custom exceptions for Events domain
# - Specific errors for event processing failures
# - Retry-aware exceptions


class EventsError(Exception):
    """Base exception for Events domain"""

    pass


class EventPublishError(EventsError):
    """Raised when event publishing fails"""

    def __init__(self, event_id: str, event_type: str, reason: str, retryable: bool = True):
        self.event_id = event_id
        self.event_type = event_type
        self.reason = reason
        self.retryable = retryable
        super().__init__(f"Failed to publish event {event_id} ({event_type}): {reason}")


class EventConsumeError(EventsError):
    """Raised when event consumption fails"""

    def __init__(self, event_id: str, event_type: str, reason: str, retryable: bool = True):
        self.event_id = event_id
        self.event_type = event_type
        self.reason = reason
        self.retryable = retryable
        super().__init__(f"Failed to consume event {event_id} ({event_type}): {reason}")


class EventValidationError(EventsError):
    """Raised when event validation fails"""

    def __init__(self, event_id: str, event_type: str, validation_errors: list[str]):
        self.event_id = event_id
        self.event_type = event_type
        self.validation_errors = validation_errors
        super().__init__(
            f"Event validation failed for {event_id} ({event_type}): {', '.join(validation_errors)}"
        )


class EventReplayError(EventsError):
    """Raised when event replay fails"""

    def __init__(self, from_timestamp: str, to_timestamp: str, reason: str):
        self.from_timestamp = from_timestamp
        self.to_timestamp = to_timestamp
        self.reason = reason
        super().__init__(f"Event replay failed ({from_timestamp} to {to_timestamp}): {reason}")


class TopicNotFoundError(EventsError):
    """Raised when Kafka topic is not found"""

    def __init__(self, topic_name: str):
        self.topic_name = topic_name
        super().__init__(f"Topic not found: {topic_name}")


class EventDeserializationError(EventsError):
    """Raised when event deserialization fails"""

    def __init__(self, raw_data: str, reason: str):
        self.raw_data = raw_data
        self.reason = reason
        super().__init__(f"Failed to deserialize event: {reason}")


class DLQError(EventsError):
    """Raised when DLQ operations fail"""

    def __init__(self, event_id: str, operation: str, reason: str):
        self.event_id = event_id
        self.operation = operation
        self.reason = reason
        super().__init__(f"DLQ {operation} failed for event {event_id}: {reason}")
