import httpx
import asyncio
from typing import Optional, Dict, Any, Union
from contextlib import asynccontextmanager
import structlog
from ..shared_logging.setup import get_correlation_id, get_trace_id


logger = structlog.get_logger(__name__)


class HttpClient:
    """Enhanced HTTP client with observability and retry support"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.default_headers = default_headers or {}

    @asynccontextmanager
    async def _client(self, **kwargs):
        """Create HTTP client with default configuration"""
        headers = self.default_headers.copy()
        
        # Add correlation and trace headers if available
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
            
        trace_id = get_trace_id()
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        
        # Merge with provided headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            **kwargs
        }
        
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            yield client

    async def _make_request(
        self,
        method: str,
        url: str,
        retries: Optional[int] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic"""
        
        retries = retries if retries is not None else self.max_retries
        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                async with self._client() as client:
                    logger.debug(
                        "Making HTTP request",
                        method=method,
                        url=url,
                        attempt=attempt + 1,
                        max_attempts=retries + 1
                    )
                    
                    response = await client.request(method, url, **kwargs)
                    
                    # Log response
                    logger.debug(
                        "HTTP response received",
                        method=method,
                        url=url,
                        status_code=response.status_code,
                        response_time_ms=response.elapsed.total_seconds() * 1000
                    )
                    
                    # Don't retry on client errors (4xx)
                    if 400 <= response.status_code < 500:
                        response.raise_for_status()
                    
                    # Retry on server errors (5xx) and specific status codes
                    if response.status_code >= 500:
                        response.raise_for_status()
                    
                    return response
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                
                if attempt < retries:
                    backoff_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        "HTTP request failed, retrying",
                        method=method,
                        url=url,
                        attempt=attempt + 1,
                        max_attempts=retries + 1,
                        error=str(e),
                        backoff_seconds=backoff_time
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(
                        "HTTP request failed after all retries",
                        method=method,
                        url=url,
                        attempts=retries + 1,
                        error=str(e)
                    )
        
        # Re-raise the last exception
        if last_exception:
            raise last_exception

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make GET request"""
        return await self._make_request("GET", url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make POST request"""
        return await self._make_request("POST", url, json=json, data=data, **kwargs)

    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make PUT request"""
        return await self._make_request("PUT", url, json=json, data=data, **kwargs)

    async def patch(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make PATCH request"""
        return await self._make_request("PATCH", url, json=json, data=data, **kwargs)

    async def delete(
        self,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make DELETE request"""
        return await self._make_request("DELETE", url, **kwargs)


class AuthenticatedHttpClient(HttpClient):
    """HTTP client that automatically adds authentication headers"""
    
    def __init__(
        self,
        auth_provider,  # Can be a function that returns auth header value
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.auth_provider = auth_provider
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix

    async def _get_auth_header(self) -> str:
        """Get authentication header value"""
        if callable(self.auth_provider):
            token = await self.auth_provider() if asyncio.iscoroutinefunction(self.auth_provider) else self.auth_provider()
        else:
            token = self.auth_provider
        
        if self.auth_prefix:
            return f"{self.auth_prefix} {token}"
        return token

    @asynccontextmanager
    async def _client(self, **kwargs):
        """Create authenticated HTTP client"""
        headers = self.default_headers.copy()
        
        # Add authentication header
        auth_header_value = await self._get_auth_header()
        headers[self.auth_header] = auth_header_value
        
        # Add correlation and trace headers
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
            
        trace_id = get_trace_id()
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        
        # Merge with provided headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            **kwargs
        }
        
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            yield client


def create_http_client(
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    **kwargs
) -> HttpClient:
    """Factory function to create HTTP client"""
    return HttpClient(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        **kwargs
    )


def create_authenticated_client(
    auth_provider,
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    **kwargs
) -> AuthenticatedHttpClient:
    """Factory function to create authenticated HTTP client"""
    return AuthenticatedHttpClient(
        auth_provider=auth_provider,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        **kwargs
    )