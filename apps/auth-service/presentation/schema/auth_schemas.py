from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class SessionResponse(BaseModel):
    """Response for cipher session creation"""
    sid: str
    server_public_key_jwk: Dict[str, Any]


class CipherEnvelopeRequest(BaseModel):
    """Cipher envelope from client"""
    client_public_key_jwk: Dict[str, Any]
    nonce: str
    password_enc: str
    sid: str


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: Optional[str] = None
    cipher_envelope: Optional[CipherEnvelopeRequest] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class SignupRequest(BaseModel):
    """User signup request"""
    email: EmailStr
    password: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_number: Optional[str] = None


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
    code: Optional[str] = None  # For OTC exchange
    refresh_token: Optional[str] = None  # For refresh


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    username: str


class ConfirmForgotPasswordRequest(BaseModel):
    """Confirm forgot password request"""
    username: str
    confirmation_code: str
    new_password: str