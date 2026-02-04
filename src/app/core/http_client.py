import httpx
from typing import Any, Dict, Optional, Union
from src.app.core.logging import logger

class HTTPClient:
    """
    A reusable asynchronous HTTP client utility using httpx.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        current_headers = {**self.headers, **(headers or {})}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=current_headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred during HTTP request: {str(e)}")
                raise

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("POST", endpoint, data=data, **kwargs)

# Global shared instance for simple use cases
http_client = HTTPClient()
