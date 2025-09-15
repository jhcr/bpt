import base64
from typing import Any

import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = structlog.get_logger(__name__)


class ECDHCipher:
    """ECDH key exchange with HKDF and AES-GCM for password encryption"""

    @staticmethod
    def generate_key_pair() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Generate ECDH key pair using P-256 curve"""
        try:
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key = private_key.public_key()
            return private_key, public_key

        except Exception as e:
            logger.error("Key pair generation failed", error=str(e))
            raise

    @staticmethod
    def public_key_to_jwk(public_key: ec.EllipticCurvePublicKey) -> dict[str, Any]:
        """Convert EC public key to JWK format"""
        try:
            # Get public key coordinates
            public_numbers = public_key.public_numbers()

            # Convert coordinates to bytes (32 bytes for P-256)
            x_bytes = public_numbers.x.to_bytes(32, "big")
            y_bytes = public_numbers.y.to_bytes(32, "big")

            # Base64URL encode coordinates
            x_b64 = base64.urlsafe_b64encode(x_bytes).decode().rstrip("=")
            y_b64 = base64.urlsafe_b64encode(y_bytes).decode().rstrip("=")

            return {"kty": "EC", "crv": "P-256", "x": x_b64, "y": y_b64, "use": "enc"}

        except Exception as e:
            logger.error("Public key to JWK conversion failed", error=str(e))
            raise

    @staticmethod
    def jwk_to_public_key(jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
        """Convert JWK to EC public key"""
        try:
            if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
                raise ValueError("Invalid JWK format")

            # Decode coordinates
            x_b64 = jwk["x"] + "=" * (4 - len(jwk["x"]) % 4)  # Add padding
            y_b64 = jwk["y"] + "=" * (4 - len(jwk["y"]) % 4)  # Add padding

            x_bytes = base64.urlsafe_b64decode(x_b64)
            y_bytes = base64.urlsafe_b64decode(y_b64)

            # Convert to integers
            x = int.from_bytes(x_bytes, "big")
            y = int.from_bytes(y_bytes, "big")

            # Create public key
            public_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
            return public_numbers.public_key()

        except Exception as e:
            logger.error("JWK to public key conversion failed", error=str(e))
            raise

    @staticmethod
    def decrypt_envelope(
        server_private_key: ec.EllipticCurvePrivateKey,
        client_public_key_jwk: dict[str, Any],
        sid: str,
        nonce: str,
        ciphertext: str,
    ) -> str:
        """
        Decrypt password envelope using ECDH + HKDF + AES-GCM

        Args:
            server_private_key: Server's private key
            client_public_key_jwk: Client's public key in JWK format
            sid: Session ID (used as salt)
            nonce: Base64URL encoded nonce
            ciphertext: Base64URL encoded ciphertext

        Returns:
            Decrypted password
        """
        try:
            # Convert client's public key from JWK
            client_public_key = ECDHCipher.jwk_to_public_key(client_public_key_jwk)

            # Perform ECDH key exchange
            shared_key = server_private_key.exchange(ec.ECDH(), client_public_key)

            # Derive encryption key using HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=sid.encode("utf-8"),
                info=b"pwd-login-v1",
            )
            derived_key = hkdf.derive(shared_key)

            # Decode nonce and ciphertext
            nonce_bytes = base64.urlsafe_b64decode(nonce + "=" * (4 - len(nonce) % 4))
            ciphertext_bytes = base64.urlsafe_b64decode(ciphertext + "=" * (4 - len(ciphertext) % 4))

            # Decrypt using AES-GCM
            aesgcm = AESGCM(derived_key)
            plaintext = aesgcm.decrypt(
                nonce_bytes,
                ciphertext_bytes,
                sid.encode("utf-8"),  # Additional authenticated data
            )

            return plaintext.decode("utf-8")

        except Exception as e:
            logger.error("Password decryption failed", sid=sid, error=str(e))
            raise

    @staticmethod
    def private_key_to_pem(private_key: ec.EllipticCurvePrivateKey) -> bytes:
        """Convert private key to PEM format"""
        try:
            return private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

        except Exception as e:
            logger.error("Private key to PEM conversion failed", error=str(e))
            raise

    @staticmethod
    def pem_to_private_key(pem_data: bytes) -> ec.EllipticCurvePrivateKey:
        """Convert PEM to private key"""
        try:
            return serialization.load_pem_private_key(pem_data, password=None)

        except Exception as e:
            logger.error("PEM to private key conversion failed", error=str(e))
            raise


def generate_cipher_session_keys(sid: str) -> tuple[bytes, dict[str, Any]]:
    """
    Generate ECDH key pair for a cipher session

    Args:
        sid: Session ID

    Returns:
        Tuple of (private_key_pem, public_key_jwk)
    """
    try:
        logger.debug("Generating cipher session keys", sid=sid)

        # Generate key pair
        private_key, public_key = ECDHCipher.generate_key_pair()

        # Convert to storage formats
        private_key_pem = ECDHCipher.private_key_to_pem(private_key)
        public_key_jwk = ECDHCipher.public_key_to_jwk(public_key)

        logger.debug("Cipher session keys generated", sid=sid)
        return private_key_pem, public_key_jwk

    except Exception as e:
        logger.error("Cipher session key generation failed", sid=sid, error=str(e))
        raise


def decrypt_password_envelope(
    private_key_pem: bytes,
    client_public_key_jwk: dict[str, Any],
    sid: str,
    nonce: str,
    ciphertext: str,
) -> str:
    """
    Decrypt password from client cipher envelope

    Args:
        private_key_pem: Server's private key in PEM format
        client_public_key_jwk: Client's public key in JWK format
        sid: Session ID
        nonce: Base64URL encoded nonce
        ciphertext: Base64URL encoded ciphertext

    Returns:
        Decrypted password
    """
    try:
        # Load private key
        private_key = ECDHCipher.pem_to_private_key(private_key_pem)

        # Decrypt
        return ECDHCipher.decrypt_envelope(
            server_private_key=private_key,
            client_public_key_jwk=client_public_key_jwk,
            sid=sid,
            nonce=nonce,
            ciphertext=ciphertext,
        )

    except Exception as e:
        logger.error("Password envelope decryption failed", sid=sid, error=str(e))
        raise
