import base64
import time
import uuid
from typing import Any

import jwt
import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = structlog.get_logger(__name__)


class ES256Signer:
    """ES256 JWT signer with JWKS support"""

    def __init__(self, kid: str, pem: bytes, iss: str, aud: str):
        """
        Initialize ES256 signer

        Args:
            kid: Key ID for JWKS
            pem: Private key in PEM format
            iss: JWT issuer
            aud: JWT audience
        """
        self.kid = kid
        self.iss = iss
        self.aud = aud

        try:
            self._private_key = serialization.load_pem_private_key(pem, password=None)
            if not isinstance(self._private_key, ec.EllipticCurvePrivateKey):
                raise ValueError("Key must be an EC private key")

            # Get public key for JWKS
            self._public_key = self._private_key.public_key()

            logger.info("ES256 signer initialized", kid=kid, iss=iss, aud=aud)

        except Exception as e:
            logger.error("Failed to initialize ES256 signer", error=str(e))
            raise

    def mint(self, sub: str, sid: str, scopes: str, extra: dict[str, Any], ttl: int = 900) -> str:
        """
        Mint a JWT token

        Args:
            sub: Subject
            sid: Session ID
            scopes: Space-delimited scopes
            extra: Additional claims
            ttl: Time to live in seconds

        Returns:
            Signed JWT token
        """
        try:
            now = int(time.time())

            # Base payload
            payload = {
                "iss": self.iss,
                "aud": self.aud,
                "sub": sub,
                "iat": now,
                "exp": now + ttl,
                "jti": extra.get("jti", str(uuid.uuid4())),
                "sid": sid,
                "scope": scopes,
                "ver": 1,
            }

            # Add extra claims (excluding jti since we handle it above)
            for key, value in extra.items():
                if key not in {"jti"} and value is not None:
                    payload[key] = value

            # Sign the token
            token = jwt.encode(payload, self._private_key, algorithm="ES256", headers={"kid": self.kid})

            logger.debug("JWT token minted", sub=sub, sid=sid, exp=payload["exp"])
            return token

        except Exception as e:
            logger.error("JWT minting failed", sub=sub, error=str(e))
            raise

    def get_jwks(self) -> dict[str, Any]:
        """Get JSON Web Key Set for this signer"""
        try:
            # Get public key coordinates
            public_numbers = self._public_key.public_numbers()

            # Convert coordinates to bytes (32 bytes for P-256)
            x_bytes = public_numbers.x.to_bytes(32, "big")
            y_bytes = public_numbers.y.to_bytes(32, "big")

            # Base64URL encode coordinates
            x_b64 = base64.urlsafe_b64encode(x_bytes).decode().rstrip("=")
            y_b64 = base64.urlsafe_b64encode(y_bytes).decode().rstrip("=")

            jwk = {
                "kty": "EC",
                "use": "sig",
                "crv": "P-256",
                "kid": self.kid,
                "x": x_b64,
                "y": y_b64,
                "alg": "ES256",
            }

            return {"keys": [jwk]}

        except Exception as e:
            logger.error("JWKS generation failed", error=str(e))
            raise

    def get_public_key_jwk(self) -> dict[str, Any]:
        """Get the public key as JWK"""
        jwks = self.get_jwks()
        return jwks["keys"][0]


def create_es256_signer(kid: str, private_key_pem: str, iss: str, aud: str) -> ES256Signer:
    """Factory function to create ES256 signer"""
    return ES256Signer(
        kid=kid,
        pem=(private_key_pem.encode() if isinstance(private_key_pem, str) else private_key_pem),
        iss=iss,
        aud=aud,
    )
