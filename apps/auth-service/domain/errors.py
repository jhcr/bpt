from enum import Enum


class ErrorCode(Enum):
    """Standard error codes for the auth domain"""

    # Authentication errors
    INVALID_CREDENTIALS = "AUTH_001"
    INVALID_TOKEN = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"

    # Session errors
    INVALID_SESSION = "SESSION_001"
    SESSION_EXPIRED = "SESSION_002"
    SESSION_NOT_FOUND = "SESSION_003"

    # User errors
    USER_NOT_FOUND = "USER_001"
    USER_ALREADY_EXISTS = "USER_002"
    USER_DISABLED = "USER_003"
    EMAIL_NOT_VERIFIED = "USER_004"

    # OAuth errors
    INVALID_AUTHORIZATION_CODE = "OAUTH_001"
    OAUTH_CLIENT_AUTH_FAILED = "OAUTH_002"
    TOKEN_EXCHANGE_FAILED = "OAUTH_003"
    INVALID_TOKEN_RESPONSE = "OAUTH_004"
    OAUTH_PROVIDER_ERROR = "OAUTH_005"

    # Registration errors
    REGISTRATION_FAILED = "REG_001"
    CONFIRMATION_REQUIRED = "REG_002"
    INVALID_CONFIRMATION_CODE = "REG_003"

    # Validation errors
    INVALID_INPUT = "VAL_001"
    MISSING_REQUIRED_FIELD = "VAL_002"

    # Infrastructure errors
    NETWORK_ERROR = "INFRA_001"
    PROVIDER_UNAVAILABLE = "INFRA_002"
    CIPHER_ERROR = "INFRA_003"
    JWT_SIGNING_ERROR = "INFRA_004"


class AuthDomainError(Exception):
    """Base exception for auth domain errors"""

    def __init__(self, message: str, error_code: ErrorCode | None = None, details: dict | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.message = message

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code.value}] {self.message}"
        return self.message


# Authentication Errors
class AuthenticationError(AuthDomainError):
    """Base class for authentication-related errors"""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid"""

    def __init__(self, message: str = "Invalid username or password", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_CREDENTIALS, details)


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid"""

    def __init__(self, message: str = "Invalid or malformed token", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_TOKEN, details)


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired"""

    def __init__(self, message: str = "Token has expired", details: dict | None = None):
        super().__init__(message, ErrorCode.TOKEN_EXPIRED, details)


class InsufficientPermissionsError(AuthenticationError):
    """Raised when user lacks required permissions"""

    def __init__(self, message: str = "Insufficient permissions", details: dict | None = None):
        super().__init__(message, ErrorCode.INSUFFICIENT_PERMISSIONS, details)


# Session Errors
class SessionError(AuthDomainError):
    """Base class for session-related errors"""

    pass


class InvalidSessionError(SessionError):
    """Raised when session is invalid"""

    def __init__(self, message: str = "Invalid session", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_SESSION, details)


class SessionExpiredError(SessionError):
    """Raised when session has expired"""

    def __init__(self, message: str = "Session has expired", details: dict | None = None):
        super().__init__(message, ErrorCode.SESSION_EXPIRED, details)


class SessionNotFoundError(SessionError):
    """Raised when session is not found"""

    def __init__(self, message: str = "Session not found", details: dict | None = None):
        super().__init__(message, ErrorCode.SESSION_NOT_FOUND, details)


# User Errors
class UserError(AuthDomainError):
    """Base class for user-related errors"""

    pass


class UserNotFoundError(UserError):
    """Raised when user is not found"""

    def __init__(self, message: str = "User not found", details: dict | None = None):
        super().__init__(message, ErrorCode.USER_NOT_FOUND, details)


class UserAlreadyExistsError(UserError):
    """Raised when user already exists"""

    def __init__(self, message: str = "User already exists", details: dict | None = None):
        super().__init__(message, ErrorCode.USER_ALREADY_EXISTS, details)


class UserDisabledError(UserError):
    """Raised when user account is disabled"""

    def __init__(self, message: str = "User account is disabled", details: dict | None = None):
        super().__init__(message, ErrorCode.USER_DISABLED, details)


class EmailNotVerifiedError(UserError):
    """Raised when email verification is required"""

    def __init__(self, message: str = "Email address not verified", details: dict | None = None):
        super().__init__(message, ErrorCode.EMAIL_NOT_VERIFIED, details)


# Registration Errors
class RegistrationError(AuthDomainError):
    """Base class for registration-related errors"""

    pass


class UserRegistrationError(RegistrationError):
    """Raised when user registration fails"""

    def __init__(self, message: str = "User registration failed", details: dict | None = None):
        super().__init__(message, ErrorCode.REGISTRATION_FAILED, details)


class ConfirmationRequiredError(RegistrationError):
    """Raised when user confirmation is required"""

    def __init__(self, message: str = "Email/SMS confirmation required", details: dict | None = None):
        super().__init__(message, ErrorCode.CONFIRMATION_REQUIRED, details)


class InvalidConfirmationCodeError(RegistrationError):
    """Raised when confirmation code is invalid"""

    def __init__(self, message: str = "Invalid confirmation code", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_CONFIRMATION_CODE, details)


# Validation Errors
class ValidationError(AuthDomainError):
    """Raised when input validation fails"""

    def __init__(self, message: str = "Input validation failed", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_INPUT, details)


class MissingRequiredFieldError(ValidationError):
    """Raised when required field is missing"""

    def __init__(self, field_name: str, details: dict | None = None):
        message = f"Required field '{field_name}' is missing"
        super().__init__(message, ErrorCode.MISSING_REQUIRED_FIELD, details)


# Infrastructure Errors
class InfrastructureError(AuthDomainError):
    """Base class for infrastructure-related errors"""

    pass


class NetworkError(InfrastructureError):
    """Raised when network operations fail"""

    def __init__(self, message: str = "Network operation failed", details: dict | None = None):
        super().__init__(message, ErrorCode.NETWORK_ERROR, details)


class ProviderUnavailableError(InfrastructureError):
    """Raised when identity provider is unavailable"""

    def __init__(self, message: str = "Identity provider unavailable", details: dict | None = None):
        super().__init__(message, ErrorCode.PROVIDER_UNAVAILABLE, details)


class CipherSessionError(InfrastructureError):
    """Raised when cipher session operations fail"""

    def __init__(self, message: str = "Cipher session operation failed", details: dict | None = None):
        super().__init__(message, ErrorCode.CIPHER_ERROR, details)


class JWTSigningError(InfrastructureError):
    """Raised when JWT signing fails"""

    def __init__(self, message: str = "JWT signing failed", details: dict | None = None):
        super().__init__(message, ErrorCode.JWT_SIGNING_ERROR, details)


# Service Errors
class ServiceError(AuthDomainError):
    """Base class for service-related errors"""

    pass


class ServiceTokenError(ServiceError):
    """Raised when service token operations fail"""

    def __init__(self, message: str = "Service token operation failed", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_TOKEN, details)


class UnauthorizedClientError(ServiceError):
    """Raised when service client is not authorized"""

    def __init__(self, message: str = "Unauthorized client", details: dict | None = None):
        super().__init__(message, ErrorCode.INSUFFICIENT_PERMISSIONS, details)


# OAuth Errors
class OAuthError(AuthDomainError):
    """Base class for OAuth-related errors"""

    pass


class InvalidAuthorizationCodeError(OAuthError):
    """Raised when authorization code is invalid or expired"""

    def __init__(self, message: str = "Authorization code is invalid or expired", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_AUTHORIZATION_CODE, details)


class OAuthClientAuthenticationError(OAuthError):
    """Raised when OAuth client authentication fails"""

    def __init__(self, message: str = "OAuth client authentication failed", details: dict | None = None):
        super().__init__(message, ErrorCode.OAUTH_CLIENT_AUTH_FAILED, details)


class TokenExchangeError(OAuthError):
    """Raised when token exchange fails"""

    def __init__(self, message: str = "Token exchange failed", details: dict | None = None):
        super().__init__(message, ErrorCode.TOKEN_EXCHANGE_FAILED, details)


class InvalidTokenResponseError(OAuthError):
    """Raised when token response is invalid or incomplete"""

    def __init__(self, message: str = "Invalid or incomplete token response", details: dict | None = None):
        super().__init__(message, ErrorCode.INVALID_TOKEN_RESPONSE, details)


class OAuthProviderError(OAuthError):
    """Raised when OAuth provider returns an error"""

    def __init__(self, error_code: str, error_description: str = "", details: dict | None = None):
        self.oauth_error_code = error_code
        self.oauth_error_description = error_description
        message = (
            f"OAuth provider error - {error_code}: {error_description}"
            if error_description
            else f"OAuth provider error - {error_code}"
        )
        super().__init__(message, ErrorCode.OAUTH_PROVIDER_ERROR, details)


# Legacy compatibility - will be removed after refactoring
class CognitoError(ProviderUnavailableError):
    """Legacy Cognito error - use ProviderUnavailableError instead"""

    def __init__(self, message: str = "Identity provider operation failed", details: dict | None = None):
        super().__init__(message, details)
