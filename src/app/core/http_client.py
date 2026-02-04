import asyncio
import httpx
from typing import Dict, Optional
from src.app.core.config import settings


class HTTPClient:
    """
    A dual-mode (Async/Sync) HTTP client utility using httpx.
    Provides persistent connection pooling with configurable SSL verification and timeout.
    
    Returns raw httpx.Response objects for maximum flexibility.
    Caller is responsible for parsing response body and handling errors.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        verify: Optional[bool] = None
    ):
        self.base_url = base_url
        # Use provided timeout, or config, or default 30.0
        self._default_timeout = timeout if timeout is not None else getattr(settings, "http_timeout", 30.0)
        self._connect_timeout = 5.0
        self.timeout = httpx.Timeout(self._default_timeout, connect=self._connect_timeout)
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # SSL verification (only configurable at client level in httpx)
        self.verify = verify if verify is not None else getattr(settings, "http_verify_ssl", True)
        
        # Async members
        self._async_client: Optional[httpx.AsyncClient] = None
        self._async_lock = asyncio.Lock()
        
        # Sync members
        self._sync_client: Optional[httpx.Client] = None

    def _get_timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        """Build httpx.Timeout, preserving connect timeout for per-request overrides."""
        if timeout is not None:
            return httpx.Timeout(timeout, connect=self._connect_timeout)
        return self.timeout

    # --- Asynchronous Implementation ---

    async def get_async_client(self) -> httpx.AsyncClient:
        async with self._async_lock:
            if self._async_client is None or self._async_client.is_closed:
                self._async_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers=self.headers,
                    verify=self.verify,
                    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
                )
            return self._async_client

    async def close_async(self):
        async with self._async_lock:
            if self._async_client and not self._async_client.is_closed:
                await self._async_client.aclose()
                self._async_client = None

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an async HTTP request. Returns raw httpx.Response.
        
        Caller must:
        - Check response.status_code or call response.raise_for_status()
        - Parse body with response.json() or response.text
        - Access headers via response.headers
        """
        client = await self.get_async_client()
        return await client.request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data,
            headers=headers,
            timeout=self._get_timeout(timeout),
            **kwargs
        )

    async def get(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return await self.request("GET", endpoint, timeout=timeout, **kwargs)

    async def post(self, endpoint: str, json_data: Optional[Dict] = None, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return await self.request("POST", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    async def put(self, endpoint: str, json_data: Optional[Dict] = None, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return await self.request("PUT", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    async def delete(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return await self.request("DELETE", endpoint, timeout=timeout, **kwargs)

    # --- Synchronous Implementation ---

    def get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
                verify=self.verify,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50)
            )
        return self._sync_client

    def close_sync(self):
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
            self._sync_client = None

    def request_sync(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.Response:
        """Make a sync HTTP request. Returns raw httpx.Response."""
        client = self.get_sync_client()
        return client.request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data,
            headers=headers,
            timeout=self._get_timeout(timeout),
            **kwargs
        )

    def get_sync(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return self.request_sync("GET", endpoint, timeout=timeout, **kwargs)

    def post_sync(self, endpoint: str, json_data: Optional[Dict] = None, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return self.request_sync("POST", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    def put_sync(self, endpoint: str, json_data: Optional[Dict] = None, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return self.request_sync("PUT", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    def delete_sync(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> httpx.Response:
        return self.request_sync("DELETE", endpoint, timeout=timeout, **kwargs)


# Global shared instance (uses settings.http_verify_ssl for SSL verification)
http_client = HTTPClient()

# Pre-configured insecure client for internal APIs
insecure_client = HTTPClient(verify=False)
