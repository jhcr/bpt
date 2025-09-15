"""JWT signer adapter implementation"""

from application.ports.jwt_signer import JWTSigner


class JWTSignerAdapter(JWTSigner):
    """Infrastructure adapter for JWT signing operations"""

    def __init__(self, signer):
        self.signer = signer

    async def sign_jwt(self, claims):
        """Sign JWT using the underlying signer"""
        return self.signer.mint(
            sub=claims.sub,
            sid=claims.sid or "default",
            scopes=claims.scope or "",
            extra=claims.to_dict(),
            ttl=claims.exp - claims.iat,
        )

    async def get_jwks(self):
        """Get JSON Web Key Set"""
        return self.signer.get_jwks()

    async def get_current_kid(self):
        """Get current key ID"""
        return self.signer.kid
