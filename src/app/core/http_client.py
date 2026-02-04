import asyncio
import httpx
from typing import Any, Dict, Optional
from src.app.core.logging import logger

class HTTPClient:
    """
    A reusable asynchronous HTTP client utility using httpx.
    This implementation uses a persistent AsyncClient with an async lock for thread safety.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout, connect=5.0)
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """
        Get or create the internal httpx.AsyncClient using an async lock to prevent race conditions.
        """
        async with self._lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers=self.headers,
                    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
                )
            return self._client

    async def close(self):
        """
        Close the internal client.
        """
        async with self._lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        client = await self.get_client()
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=data,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            
            # Basic check for JSON content type
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} for {method} {endpoint}: {e.response.text[:200]}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request failed for {method} {endpoint}: {e}")
            raise

    async def get(self, endpoint: str, **kwargs) -> Any:
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> Any:
        return await self.request("POST", endpoint, **kwargs)

# Global shared instance
http_client = HTTPClient()
