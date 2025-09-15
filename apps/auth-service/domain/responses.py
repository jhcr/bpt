"""Use case response DTOs for auth service"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginResponse:
    """Response for user login"""

    sid: str
    access_token: str
    token_type: str
    expires_in: int
    user: "UserInfo"


@dataclass(frozen=True)
class RefreshTokenResponse:
    """Response for token refresh"""

    access_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True)
class LogoutResponse:
    """Response for user logout"""

    success: bool
    message: str
    sessions_terminated: int = 0


@dataclass(frozen=True)
class ForgotPasswordResponse:
    """Response for forgot password initiation"""

    message: str
    delivery_medium: str | None = None
    destination: str | None = None


@dataclass(frozen=True)
class ConfirmForgotPasswordResponse:
    """Response for forgot password confirmation"""

    success: bool
    message: str


@dataclass(frozen=True)
class RegisterUserResponse:
    """Response for user registration"""

    user_sub: str
    confirmation_required: bool
    delivery_medium: str | None = None
    destination: str | None = None


@dataclass(frozen=True)
class UserInfo:
    """User information for responses"""

    id: str
    email: str
    given_name: str | None
    family_name: str | None
    email_verified: bool

    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        else:
            return self.email.split("@")[0] if self.email else self.id


@dataclass(frozen=True)
class ProviderTokenInfo:
    """Provider token information (renamed from CognitoTokens)"""

    access_token: str
    id_token: str | None
    refresh_token: str | None


@dataclass(frozen=True)
class OAuthCallbackResponse:
    """Response for OAuth callback processing"""

    sid: str
    access_token: str
    token_type: str
    expires_in: int
    user: UserInfo
    provider_tokens: ProviderTokenInfo


@dataclass(frozen=True)
class OAuthStateValidation:
    """OAuth state validation result"""

    valid: bool
    redirect_after_login: str | None = None
    error: str | None = None
