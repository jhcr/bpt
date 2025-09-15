from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AccessToken:
    """Value object for access tokens"""

    token: str
    expires_in: int
    token_type: str = "Bearer"
    scope: str | None = None

    def is_expired(self, issued_at: datetime) -> bool:
        """Check if token is expired based on issue time"""
        elapsed = (datetime.utcnow() - issued_at).total_seconds()
        return elapsed >= self.expires_in


@dataclass(frozen=True)
class RefreshToken:
    """Value object for refresh tokens"""

    token: str
    expires_in: int | None = None  # Long-lived tokens might not have expiration


@dataclass(frozen=True)
class ServiceToken:
    """Value object for service-to-service tokens"""

    token: str
    expires_in: int
    sub_spn: str
    scope: str
    token_type: str = "Bearer"
    actor_sub: str | None = None
    actor_scope: str | None = None
    actor_roles: list[str] | None = None


@dataclass(frozen=True)
class JWTClaims:
    """Value object for JWT claims"""

    # Standard claims
    iss: str  # Issuer
    sub: str  # Subject
    aud: str  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: str  # JWT ID

    # Auth-specific claims
    auth_time: int | None = None
    azp: str | None = None  # Authorized party
    amr: list[str] | None = None  # Authentication methods

    # Application claims
    sid: str | None = None  # Session ID
    sidv: int | None = None  # Session version
    roles: list[str] | None = None
    scope: str | None = None
    idp: str | None = None  # Identity provider
    tenant_id: str | None = None
    provider_sub: str | None = None
    ver: int = 1

    # Service token claims
    token_use: str = "access"  # "access" or "svc"
    act: dict[str, Any] | None = None  # Actor claim for service tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JWT encoding"""
        result = {
            "iss": self.iss,
            "sub": self.sub,
            "aud": self.aud,
            "exp": self.exp,
            "iat": self.iat,
            "jti": self.jti,
            "ver": self.ver,
            "token_use": self.token_use,
        }

        # Add optional claims if present
        optional_claims = [
            "auth_time",
            "azp",
            "amr",
            "sid",
            "sidv",
            "roles",
            "scope",
            "idp",
            "tenant_id",
            "provider_sub",
            "act",
        ]

        for claim in optional_claims:
            value = getattr(self, claim)
            if value is not None:
                result[claim] = value

        return result


@dataclass(frozen=True)
class CipherEnvelope:
    """Encrypted password envelope from client"""

    client_public_key_jwk: dict[str, Any]
    nonce: str  # Base64URL encoded
    password_enc: str  # Base64URL encoded ciphertext
    sid: str  # Session ID for KDF salt
