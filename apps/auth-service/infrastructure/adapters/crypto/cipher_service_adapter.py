"""Cipher service adapter implementation"""

from application.ports.jwt_signer import CipherService


class CipherServiceAdapter(CipherService):
    """Infrastructure adapter for cipher operations using ECDH KMS"""

    async def generate_cipher_session(self, sid: str):
        """Generate cipher session keys using ECDH KMS"""
        from infrastructure.adapters.crypto.ecdh_kms import (
            generate_cipher_session_keys,
        )

        return generate_cipher_session_keys(sid)

    async def decrypt_password(self, private_key_pem, client_public_key_jwk, sid, nonce, ciphertext):
        """Decrypt password envelope using ECDH KMS"""
        from infrastructure.adapters.crypto.ecdh_kms import (
            decrypt_password_envelope,
        )

        return decrypt_password_envelope(private_key_pem, client_public_key_jwk, sid, nonce, ciphertext)
