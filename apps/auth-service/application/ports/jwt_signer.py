from abc import ABC, abstractmethod
from typing import Any

from domain.value_objects.tokens import JWTClaims


class JWTSigner(ABC):
    """Port for JWT signing operations"""

    @abstractmethod
    async def sign_jwt(self, claims: JWTClaims) -> str:
        """Sign a JWT with the given claims"""
        pass

    @abstractmethod
    async def get_jwks(self) -> dict[str, Any]:
        """Get JSON Web Key Set for token verification"""
        pass

    @abstractmethod
    async def get_current_kid(self) -> str:
        """Get the current key ID being used for signing"""
        pass


class CipherService(ABC):
    """Port for cryptographic operations"""

    @abstractmethod
    async def generate_cipher_session(self, sid: str) -> tuple[bytes, dict[str, Any]]:
        """
        Generate ECDH key pair for cipher session
        Returns (private_key_pem, public_key_jwk)
        """
        pass

    @abstractmethod
    async def decrypt_password(
        self,
        private_key_pem: bytes,
        client_public_key_jwk: dict[str, Any],
        sid: str,
        nonce: str,
        ciphertext: str,
    ) -> str:
        """Decrypt password using ECDH + HKDF + AES-GCM"""
        pass
