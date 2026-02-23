"""HTTP/API tool for making HTTP requests."""

from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolOutput
from app.core.logging import logger


class HTTPToolInput(BaseModel):
    """Input schema for HTTP tool."""
    method: str = Field(
        default="GET",
        description="HTTP method (GET, POST, PUT, DELETE, etc.)"
    )
    url: str = Field(..., description="Full URL to call")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional HTTP headers"
    )
    body: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional request body (for POST, PUT, etc.)"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )


class HTTPTool(BaseTool):
    """
    Tool for making HTTP requests to external APIs.
    
    Use this tool to:
    - Query REST APIs
    - Fetch data from URLs
    - Call webhooks
    - POST/PUT/DELETE to endpoints
    """
    
    @property
    def name(self) -> str:
        return "http"
    
    @property
    def description(self) -> str:
        return "Make HTTP requests to external APIs and URLs"
    
    @property
    def input_schema(self) -> type[BaseModel]:
        return HTTPToolInput

    @property
    def required_fields(self) -> list[str]:
        return ["url"]
    
    def execute(self, **kwargs) -> ToolOutput:
        """Execute HTTP request."""
        try:
            # Clean up input data from LLM
            # The LLM may generate invalid types, so we normalize them
            if kwargs.get("body") == "" or kwargs.get("body") == {}:
                kwargs["body"] = None
            if kwargs.get("headers") == {}:
                kwargs["headers"] = None
            if isinstance(kwargs.get("timeout"), str):
                try:
                    kwargs["timeout"] = int(kwargs["timeout"])
                except (ValueError, TypeError):
                    kwargs["timeout"] = 30
            
            # Parse input
            input_data = HTTPToolInput(**kwargs)
            
            logger.debug(f"HTTP {input_data.method} {input_data.url}")
            
            # Prepare headers with default User-Agent
            headers = input_data.headers or {}
            if "user-agent" not in {k.lower() for k in headers.keys()}:
                headers = {
                    **headers,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            
            # Make request
            with httpx.Client(timeout=input_data.timeout) as client:
                response = client.request(
                    method=input_data.method,
                    url=input_data.url,
                    headers=headers,
                    json=input_data.body if input_data.method in ["POST", "PUT", "PATCH"] else None,
                )
                
                # Parse response
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text
                
                result = {
                    "status_code": response.status_code,
                    "body": response_data,
                    "headers": dict(response.headers),
                }
                
                if 200 <= response.status_code < 300:
                    logger.debug(f"HTTP request succeeded: {response.status_code}")
                    return ToolOutput(success=True, result=result)
                else:
                    error_msg = f"HTTP {response.status_code}: {response_data}"
                    logger.warning(error_msg)
                    return ToolOutput(success=False, result=result, error=error_msg)
        
        except Exception as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            return ToolOutput(success=False, result=None, error=error_msg)
