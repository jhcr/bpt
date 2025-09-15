# Assumptions:
# - Using pytest for testing framework
# - Testing ES256 JWT signing and JWKS generation
# - Mocking private key for deterministic tests

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from infrastructure.adapters.crypto.es256_signer import ES256Signer


@pytest.fixture
def test_private_key():
    """Generate test EC private key"""
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def test_private_key_pem(test_private_key):
    """Get test private key as PEM bytes"""
    from cryptography.hazmat.primitives import serialization

    return test_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture
def signer(test_private_key_pem):
    """Create ES256Signer instance"""
    return ES256Signer(kid="test-key-id", pem=test_private_key_pem, iss="https://auth.test.com", aud="test-audience")


class TestES256Signer:
    """Test cases for ES256Signer"""

    def test_init_success(self, test_private_key_pem):
        """Test successful initialization"""
        signer = ES256Signer(kid="test-key", pem=test_private_key_pem, iss="https://test.com", aud="test-aud")

        assert signer.kid == "test-key"
        assert signer.iss == "https://test.com"
        assert signer.aud == "test-aud"

    def test_init_invalid_key(self):
        """Test initialization with invalid key"""
        with pytest.raises((ValueError, TypeError)):
            ES256Signer(kid="test-key", pem=b"invalid-pem-data", iss="https://test.com", aud="test-aud")

    def test_mint_basic_token(self, signer):
        """Test minting basic JWT token"""
        token = signer.mint(
            sub="test-subject", sid="test-session", scopes="user.read user.write", extra={"test_claim": "test_value"}
        )

        assert isinstance(token, str)

        # Decode without verification to check payload
        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded["iss"] == "https://auth.test.com"
        assert decoded["aud"] == "test-audience"
        assert decoded["sub"] == "test-subject"
        assert decoded["sid"] == "test-session"
        assert decoded["scope"] == "user.read user.write"
        assert decoded["ver"] == 1
        assert decoded["test_claim"] == "test_value"
        assert "iat" in decoded
        assert "exp" in decoded
        assert "jti" in decoded

    def test_mint_with_ttl(self, signer):
        """Test minting token with custom TTL"""
        start_time = int(time.time())
        token = signer.mint(sub="test-subject", sid="test-session", scopes="user.read", extra={}, ttl=3600)

        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded["exp"] - decoded["iat"] == 3600
        assert decoded["iat"] >= start_time

    def test_mint_service_token(self, signer):
        """Test minting service token with actor"""
        token = signer.mint(
            sub="spn:bff",
            sid="svc",
            scopes="svc.userprofiles.read",
            extra={
                "token_use": "svc",
                "amr": ["svc"],
                "act": {"sub": "user-uuid", "scope": "user.read", "roles": ["user"]},
            },
        )

        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded["sub"] == "spn:bff"
        assert decoded["token_use"] == "svc"
        assert decoded["amr"] == ["svc"]
        assert decoded["act"]["sub"] == "user-uuid"
        assert decoded["act"]["scope"] == "user.read"
        assert decoded["act"]["roles"] == ["user"]

    def test_get_jwks(self, signer):
        """Test JWKS generation"""
        jwks = signer.get_jwks()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1

        jwk = jwks["keys"][0]
        assert jwk["kty"] == "EC"
        assert jwk["use"] == "sig"
        assert jwk["crv"] == "P-256"
        assert jwk["kid"] == "test-key-id"
        assert jwk["alg"] == "ES256"
        assert "x" in jwk
        assert "y" in jwk

    def test_get_public_key_jwk(self, signer):
        """Test getting single public key JWK"""
        jwk = signer.get_public_key_jwk()

        assert jwk["kty"] == "EC"
        assert jwk["use"] == "sig"
        assert jwk["kid"] == "test-key-id"
