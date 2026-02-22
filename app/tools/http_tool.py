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
    
    def execute(self, **kwargs) -> ToolOutput:
        """Execute HTTP request."""
        try:
            # Parse input
            input_data = HTTPToolInput(**kwargs)
            
            logger.debug(f"HTTP {input_data.method} {input_data.url}")
            
            # Make request
            with httpx.Client(timeout=input_data.timeout) as client:
                response = client.request(
                    method=input_data.method,
                    url=input_data.url,
                    headers=input_data.headers or {},
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
