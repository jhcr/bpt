import threading
import time
from dataclasses import dataclass

import httpx


@dataclass
class ServiceTokenResponse:
    access_token: str
    token_type: str
    expires_in: int


class ServiceTokenClient:
    """Client for obtaining and caching service tokens"""

    def __init__(
        self,
        auth_base: str,
        client_id: str,
        client_secret: str,
        sub_spn: str,
        scope: str,
    ):
        self.auth_base = auth_base.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.sub_spn = sub_spn
        self.scope = scope
        self._lock = threading.Lock()
        self._cache: dict[str, tuple] = {}  # cache_key -> (token, exp_time)

    def get(
        self,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
    ) -> str:
        """
        Get a service token, using cache when possible
        Returns the access_token string
        """
        cache_key = self._make_cache_key(actor_sub, actor_scope, actor_roles)

        with self._lock:
            # Check cache first
            if cache_key in self._cache:
                token, exp_time = self._cache[cache_key]
                if time.time() < exp_time - 60:  # 60s buffer
                    return token

            # Fetch new token
            token_response = self._fetch_token(actor_sub, actor_scope, actor_roles)

            # Cache it
            exp_time = time.time() + token_response.expires_in
            self._cache[cache_key] = (token_response.access_token, exp_time)

            return token_response.access_token

    def _fetch_token(
        self,
        actor_sub: str | None,
        actor_scope: str | None,
        actor_roles: list[str] | None,
    ) -> ServiceTokenResponse:
        """Fetch a new service token from the auth service"""
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "sub_spn": self.sub_spn,
            "scope": self.scope,
        }

        if actor_sub:
            payload["actor_sub"] = actor_sub
        if actor_scope:
            payload["actor_scope"] = actor_scope
        if actor_roles:
            payload["actor_roles"] = actor_roles

        try:
            response = httpx.post(f"{self.auth_base}/auth/svc/token", json=payload, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            return ServiceTokenResponse(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=data["expires_in"],
            )
        except httpx.RequestError as e:
            raise ServiceTokenError(f"Failed to fetch service token: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ServiceTokenError(f"Service token request failed: {e.response.status_code} {e.response.text}") from e

    def _make_cache_key(
        self,
        actor_sub: str | None,
        actor_scope: str | None,
        actor_roles: list[str] | None,
    ) -> str:
        """Create a cache key for the token request"""
        parts = [self.sub_spn, self.scope]
        if actor_sub:
            parts.append(f"actor:{actor_sub}")
        if actor_scope:
            parts.append(f"scope:{actor_scope}")
        if actor_roles:
            parts.append(f"roles:{','.join(sorted(actor_roles))}")
        return "|".join(parts)

    def clear_cache(self):
        """Clear the token cache"""
        with self._lock:
            self._cache.clear()


class ServiceTokenError(Exception):
    """Exception raised for service token operations"""

    pass


class ServiceTokenHttpClient:
    """HTTP client that automatically adds service tokens to requests"""

    def __init__(
        self,
        service_token_client: ServiceTokenClient,
        base_url: str,
        timeout: float = 5.0,
    ):
        self.svc_token = service_token_client
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get(
        self,
        path: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a GET request with service token"""
        return await self._request("GET", path, actor_sub, actor_scope, actor_roles, **kwargs)

    async def post(
        self,
        path: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a POST request with service token"""
        return await self._request("POST", path, actor_sub, actor_scope, actor_roles, **kwargs)

    async def put(
        self,
        path: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a PUT request with service token"""
        return await self._request("PUT", path, actor_sub, actor_scope, actor_roles, **kwargs)

    async def delete(
        self,
        path: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a DELETE request with service token"""
        return await self._request("DELETE", path, actor_sub, actor_scope, actor_roles, **kwargs)

    async def _request(
        self,
        method: str,
        path: str,
        actor_sub: str | None,
        actor_scope: str | None,
        actor_roles: list[str] | None,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with service token"""
        token = self.svc_token.get(actor_sub, actor_scope, actor_roles)

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers

        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
