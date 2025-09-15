"""Provider-agnostic domain entities for authentication"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticationChallenge:
    """Authentication challenge from provider"""

    challenge_name: str | None = None
    session: str | None = None
    authentication_result: "AuthenticationResult | None" = None


@dataclass(frozen=True)
class AuthenticationResult:
    """Authentication result with tokens"""

    access_token: str
    expires_in: int
    token_type: str
    refresh_token: str | None = None
    id_token: str | None = None


@dataclass(frozen=True)
class UserAttributes:
    """User attributes from identity provider"""

    sub: str
    email: str | None = None
    email_verified: bool = False
    given_name: str | None = None
    family_name: str | None = None
    phone_number: str | None = None
    phone_number_verified: bool = False
    preferred_username: str | None = None
    picture: str | None = None
    locale: str | None = None
    zoneinfo: str | None = None

    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        elif self.preferred_username:
            return self.preferred_username
        elif self.email:
            return self.email.split("@")[0]
        else:
            return self.sub


@dataclass(frozen=True)
class ProviderUser:
    """User data from identity provider"""

    username: str
    user_attributes: UserAttributes
    user_status: str | None = None
    enabled: bool = True

    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.enabled and self.user_status in ("CONFIRMED", "FORCE_CHANGE_PASSWORD")

    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        return self.user_attributes.display_name


@dataclass(frozen=True)
class AdminProviderUser:
    """Extended user data from identity provider admin API"""

    username: str
    user_attributes: UserAttributes
    user_status: str
    enabled: bool
    user_create_date: datetime | None = None
    user_last_modified_date: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.enabled and self.user_status in ("CONFIRMED", "FORCE_CHANGE_PASSWORD")


@dataclass(frozen=True)
class CodeDeliveryDetails:
    """Code delivery details from identity provider"""

    delivery_medium: str
    destination: str
    attribute_name: str | None = None

    @property
    def is_email(self) -> bool:
        """Check if delivery is via email"""
        return self.delivery_medium.upper() == "EMAIL"

    @property
    def is_sms(self) -> bool:
        """Check if delivery is via SMS"""
        return self.delivery_medium.upper() == "SMS"


@dataclass(frozen=True)
class UserRegistration:
    """User registration result"""

    user_sub: str
    user_confirmed: bool = False
    code_delivery_details: CodeDeliveryDetails | None = None

    @property
    def requires_confirmation(self) -> bool:
        """Check if user requires email/SMS confirmation"""
        return not self.user_confirmed


@dataclass(frozen=True)
class ConfirmationResult:
    """Generic confirmation result"""

    success: bool = True


@dataclass(frozen=True)
class ResendCodeResult:
    """Code resend result"""

    code_delivery_details: CodeDeliveryDetails


@dataclass(frozen=True)
class PasswordResetRequest:
    """Password reset request result"""

    code_delivery_details: CodeDeliveryDetails


@dataclass(frozen=True)
class PasswordResetConfirmation:
    """Password reset confirmation result"""

    success: bool = True


@dataclass(frozen=True)
class ResetPasswordResult:
    """Password reset completion result"""

    message: str


@dataclass(frozen=True)
class TokenRefreshResult:
    """Token refresh result"""

    authentication_result: AuthenticationResult


@dataclass(frozen=True)
class TokenSet:
    """OAuth token set from provider"""

    access_token: str
    token_type: str
    expires_in: int | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None

    @property
    def has_refresh_token(self) -> bool:
        """Check if token set includes refresh token"""
        return self.refresh_token is not None

    @property
    def has_id_token(self) -> bool:
        """Check if token set includes ID token"""
        return self.id_token is not None
