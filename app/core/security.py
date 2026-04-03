"""Optional API authentication and in-memory rate limiting middleware."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
import time
import uuid
from typing import Deque, Dict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings


class APISecurityMiddleware(BaseHTTPMiddleware):
    """Apply optional API auth and optional in-memory rate limiting for API routes.

    Behavior:
    - If API auth is disabled, auth checks are skipped.
    - If rate limit is disabled, rate checks are skipped.
    - This middleware targets only `/api/*` routes and ignores health/docs.
    """

    def __init__(self, app):
        super().__init__(app)
        self._rate_windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        if not path.startswith("/api/"):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        if settings.REQUIRE_TENANT_HEADER and not request.headers.get("X-Tenant-ID"):
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing required header: X-Tenant-ID"},
                headers={"X-Request-ID": request_id},
            )

        if settings.API_AUTH_ENABLED:
            expected = settings.API_AUTH_TOKEN or ""
            received = request.headers.get("X-API-Key", "")
            if not expected or received != expected:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: invalid API key"},
                    headers={"X-Request-ID": request_id},
                )

        if settings.RATE_LIMIT_ENABLED:
            client_ip = request.client.host if request.client else "unknown"
            if self._is_rate_limited(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please retry later."},
                    headers={"X-Request-ID": request_id},
                )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Return True when the client exceeds request quota in rolling 60s window."""
        now = time.monotonic()
        window_seconds = 60.0
        limit = max(1, settings.RATE_LIMIT_REQUESTS_PER_MINUTE)

        with self._lock:
            bucket = self._rate_windows[client_ip]
            while bucket and (now - bucket[0]) > window_seconds:
                bucket.popleft()

            if len(bucket) >= limit:
                return True

            bucket.append(now)
            return False
