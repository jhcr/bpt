# Assumptions:
# - Event entity represents domain events in the system
# - Immutable structure with metadata and payload
# - Support for correlation and trace IDs

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """Domain event entity"""

    event_id: str
    event_type: str
    user_id: str | None
    timestamp: datetime
    payload: dict[str, Any]
    metadata: dict[str, Any]
    version: int = 1

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        user_id: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        source: str = "unknown",
    ) -> "Event":
        """Create new domain event"""
        now = datetime.utcnow()

        metadata = {
            "source": source,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "trace_id": trace_id or str(uuid.uuid4()),
            "created_at": now.isoformat(),
        }

        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            timestamp=now,
            payload=payload,
            metadata=metadata,
        )

    def with_retry_metadata(
        self, retry_count: int, original_timestamp: datetime | None = None
    ) -> "Event":
        """Create event copy with retry metadata"""
        retry_metadata = {
            **self.metadata,
            "retry_count": retry_count,
            "original_timestamp": (original_timestamp or self.timestamp).isoformat(),
            "retried_at": datetime.utcnow().isoformat(),
        }

        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            user_id=self.user_id,
            timestamp=self.timestamp,
            payload=self.payload,
            metadata=retry_metadata,
            version=self.version,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "metadata": self.metadata,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            user_id=data.get("user_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data["payload"],
            metadata=data["metadata"],
            version=data.get("version", 1),
        )
