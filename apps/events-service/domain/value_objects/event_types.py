# Assumptions:
# - Event types as constants for consistency
# - Versioned event types for schema evolution
# - Clear naming convention with service prefix

from enum import Enum


class EventType(str, Enum):
    """Domain event types"""

    # User Profile Events
    USER_PROFILE_CREATED = "userprofiles.created.v1"
    USER_PROFILE_UPDATED = "userprofiles.updated.v1"
    USER_PROFILE_DELETED = "userprofiles.deleted.v1"
    USER_PROFILE_ACTIVATED = "userprofiles.activated.v1"
    USER_PROFILE_DEACTIVATED = "userprofiles.deactivated.v1"

    # User Settings Events
    USER_SETTINGS_CREATED = "usersettings.created.v1"
    USER_SETTINGS_UPDATED = "usersettings.updated.v1"
    USER_SETTINGS_DELETED = "usersettings.deleted.v1"
    USER_SETTINGS_BULK_DELETED = "usersettings.bulk_deleted.v1"

    # Authentication Events
    USER_LOGIN = "auth.login.v1"
    USER_LOGOUT = "auth.logout.v1"
    USER_TOKEN_REFRESHED = "auth.token_refreshed.v1"
    USER_PASSWORD_CHANGED = "auth.password_changed.v1"
    USER_SESSION_EXPIRED = "auth.session_expired.v1"

    # System Events
    SYSTEM_ERROR = "system.error.v1"
    SYSTEM_MAINTENANCE_STARTED = "system.maintenance_started.v1"
    SYSTEM_MAINTENANCE_COMPLETED = "system.maintenance_completed.v1"

    # Integration Events
    EXTERNAL_SYNC_STARTED = "integration.sync_started.v1"
    EXTERNAL_SYNC_COMPLETED = "integration.sync_completed.v1"
    EXTERNAL_SYNC_FAILED = "integration.sync_failed.v1"


class TopicName(str, Enum):
    """Kafka topic names"""

    USER_EVENTS = "user-events"
    SYSTEM_EVENTS = "system-events"
    INTEGRATION_EVENTS = "integration-events"
    DLQ_EVENTS = "dlq-events"


# Event type to topic mapping
EVENT_TOPIC_MAPPING = {
    # User events
    EventType.USER_PROFILE_CREATED: TopicName.USER_EVENTS,
    EventType.USER_PROFILE_UPDATED: TopicName.USER_EVENTS,
    EventType.USER_PROFILE_DELETED: TopicName.USER_EVENTS,
    EventType.USER_PROFILE_ACTIVATED: TopicName.USER_EVENTS,
    EventType.USER_PROFILE_DEACTIVATED: TopicName.USER_EVENTS,
    EventType.USER_SETTINGS_CREATED: TopicName.USER_EVENTS,
    EventType.USER_SETTINGS_UPDATED: TopicName.USER_EVENTS,
    EventType.USER_SETTINGS_DELETED: TopicName.USER_EVENTS,
    EventType.USER_SETTINGS_BULK_DELETED: TopicName.USER_EVENTS,
    EventType.USER_LOGIN: TopicName.USER_EVENTS,
    EventType.USER_LOGOUT: TopicName.USER_EVENTS,
    EventType.USER_TOKEN_REFRESHED: TopicName.USER_EVENTS,
    EventType.USER_PASSWORD_CHANGED: TopicName.USER_EVENTS,
    EventType.USER_SESSION_EXPIRED: TopicName.USER_EVENTS,
    # System events
    EventType.SYSTEM_ERROR: TopicName.SYSTEM_EVENTS,
    EventType.SYSTEM_MAINTENANCE_STARTED: TopicName.SYSTEM_EVENTS,
    EventType.SYSTEM_MAINTENANCE_COMPLETED: TopicName.SYSTEM_EVENTS,
    # Integration events
    EventType.EXTERNAL_SYNC_STARTED: TopicName.INTEGRATION_EVENTS,
    EventType.EXTERNAL_SYNC_COMPLETED: TopicName.INTEGRATION_EVENTS,
    EventType.EXTERNAL_SYNC_FAILED: TopicName.INTEGRATION_EVENTS,
}
