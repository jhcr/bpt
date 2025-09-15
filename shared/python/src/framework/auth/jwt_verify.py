# Assumptions:
# - JWT tokens use ES256 algorithm
# - JWKS endpoint is available and cached
# - Tokens have standard claims (iss, aud, sub, exp, iat)

import time
from threading import Lock
from typing import Any

import httpx
import jwt


class JWKSClient:
    def __init__(self, jwks_uri: str, cache_ttl: int = 300):
        self.jwks_uri = jwks_uri
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_time = 0
        self._lock = Lock()

    def get_signing_key(self, kid: str) -> Any:
        with self._lock:
            if time.time() - self._cache_time > self.cache_ttl:
                self._refresh_cache()

            if kid not in self._cache:
                raise jwt.PyJWTError(f"Key ID {kid} not found in JWKS")

            return jwt.algorithms.RSAAlgorithm.from_jwk(self._cache[kid])

    def _refresh_cache(self):
        try:
            response = httpx.get(self.jwks_uri, timeout=5.0)
            response.raise_for_status()
            jwks = response.json()

            self._cache = {}
            for key in jwks.get("keys", []):
                self._cache[key["kid"]] = key

            self._cache_time = time.time()
        except Exception as e:
            if not self._cache:
                raise jwt.PyJWTError(f"Failed to fetch JWKS: {e}") from e


class JWTVerifier:
    def __init__(self, jwks_client: JWKSClient, issuer: str, audience: str):
        self.jwks_client = jwks_client
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> dict[str, Any]:
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise jwt.PyJWTError("Token missing kid in header")

            # Get signing key
            signing_key = self.jwks_client.get_signing_key(kid)

            # Verify token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["ES256", "RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise jwt.PyJWTError("Token has expired") from None
        except jwt.InvalidTokenError as e:
            raise jwt.PyJWTError(f"Invalid token: {e}") from e


def create_jwt_verifier(jwks_uri: str, issuer: str, audience: str) -> JWTVerifier:
    jwks_client = JWKSClient(jwks_uri)
    return JWTVerifier(jwks_client, issuer, audience)
