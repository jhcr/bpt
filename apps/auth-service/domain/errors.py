class AuthDomainError(Exception):
    """Base exception for auth domain errors"""
    pass


class InvalidSessionError(AuthDomainError):
    """Raised when session is invalid or expired"""
    pass


class InvalidTokenError(AuthDomainError):
    """Raised when token is invalid"""
    pass


class InvalidCredentialsError(AuthDomainError):
    """Raised when credentials are invalid"""
    pass


class UserNotFoundError(AuthDomainError):
    """Raised when user is not found"""
    pass


class SessionExpiredError(AuthDomainError):
    """Raised when session has expired"""
    pass


class CipherSessionError(AuthDomainError):
    """Raised when cipher session operations fail"""
    pass


class ServiceTokenError(AuthDomainError):
    """Raised when service token operations fail"""
    pass


class UnauthorizedClientError(AuthDomainError):
    """Raised when service client is not authorized"""
    pass


class JWTSigningError(AuthDomainError):
    """Raised when JWT signing fails"""
    pass


class CognitoError(AuthDomainError):
    """Raised when Cognito operations fail"""
    pass