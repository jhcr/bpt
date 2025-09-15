from typing import Any

from pydantic import BaseModel, EmailStr


class SessionResponse(BaseModel):
    """Response for cipher session creation"""

    sid: str
    server_public_key_jwk: dict[str, Any]


class CipherEnvelopeRequest(BaseModel):
    """Cipher envelope from client"""

    client_public_key_jwk: dict[str, Any]
    nonce: str
    password_enc: str
    sid: str


class LoginRequest(BaseModel):
    """Login request"""

    username: str
    password: str | None = None
    cipher_envelope: CipherEnvelopeRequest | None = None
    device_info: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class LoginResponse(BaseModel):
    """Login response"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class SignupRequest(BaseModel):
    """User signup request"""

    email: EmailStr
    password: str
    given_name: str | None = None
    family_name: str | None = None
    phone_number: str | None = None


class SignupResponse(BaseModel):
    """Signup response"""

    message: str
    requires_confirmation: bool = True


class ConfirmSignupRequest(BaseModel):
    """Confirm signup request"""

    username: str
    confirmation_code: str


class TokenRequest(BaseModel):
    """Token exchange request"""

    grant_type: str = "authorization_code"
    code: str | None = None  # For OTC exchange
    refresh_token: str | None = None  # For refresh


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""

    username: str


class ConfirmForgotPasswordRequest(BaseModel):
    """Confirm forgot password request"""

    username: str
    confirmation_code: str
    new_password: str


class ResendConfirmationRequest(BaseModel):
    """Resend confirmation code request"""

    username: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    """Logout request"""

    global_logout: bool = False
