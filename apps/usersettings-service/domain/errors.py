# Assumptions:
# - Custom exceptions for UserSettings domain
# - Version conflict for OCC
# - Not found errors for missing settings


class UserSettingsError(Exception):
    """Base exception for UserSettings domain"""

    pass


class UserSettingNotFoundError(UserSettingsError):
    """Raised when user setting is not found"""

    def __init__(self, user_id: str, category: str):
        self.user_id = user_id
        self.category = category
        super().__init__(f"User setting not found: user_id={user_id}, category={category}")


class VersionConflictError(UserSettingsError):
    """Raised when there's a version conflict (optimistic concurrency control)"""

    def __init__(self, user_id: str, category: str, expected_version: int, actual_version: int):
        self.user_id = user_id
        self.category = category
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Version conflict: user_id={user_id}, category={category}, "
            f"expected={expected_version}, actual={actual_version}"
        )


class UserSettingValidationError(UserSettingsError):
    """Raised when user setting data validation fails"""

    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)
