from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class User:
    """Domain entity representing a user"""

    id: str
    provider_sub: str  # Provider-agnostic subject identifier
    email: str
    email_verified: bool
    phone_number: str | None = None
    phone_verified: bool = False
    given_name: str | None = None
    family_name: str | None = None
    preferred_username: str | None = None
    picture: str | None = None
    locale: str | None = None
    zoneinfo: str | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None
    enabled: bool = True
    user_status: str = "CONFIRMED"
    mfa_options: list[dict] = None
    provider_metadata: dict | None = None  # Provider-specific metadata

    def __post_init__(self):
        if self.mfa_options is None:
            self.mfa_options = []

    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        elif self.preferred_username:
            return self.preferred_username
        else:
            return self.email.split("@")[0]

    def is_active(self) -> bool:
        """Check if user is active"""
        return self.enabled and self.user_status == "CONFIRMED"

    def is_email_verified(self) -> bool:
        """Check if user's email is verified"""
        return self.email_verified

    def has_mfa_enabled(self) -> bool:
        """Check if user has MFA enabled"""
        return len(self.mfa_options) > 0


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user with token information"""

    user: User
    access_token: str
    refresh_token: str | None
    id_token: str | None
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    auth_time: datetime = None
    amr: list[str] = None  # Authentication Methods References
    idp: str = "cognito"  # Identity Provider

    def __post_init__(self):
        if self.auth_time is None:
            self.auth_time = datetime.utcnow()
        if self.amr is None:
            self.amr = ["pwd"]


@dataclass
class ServiceToken:
    """Represents a service token for service-to-service authentication"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 300  # 5 minutes
    scope: str | None = None
    sub_spn: str | None = None  # Service principal name
    actor_sub: str | None = None  # Acting user subject for on-behalf-of calls
    issued_at: datetime = None

    def __post_init__(self):
        if self.issued_at is None:
            self.issued_at = datetime.utcnow()

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time"""
        return self.issued_at + timedelta(seconds=self.expires_in)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
