"""Security, authentication, correlation ID, and rate limiting middleware."""

import os
import uuid
import logging
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.rate_limiter import limiter

logger = logging.getLogger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching X-Correlation-ID to every incoming HTTP request and response."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in state
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware applying rate limits to API requests."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/ready", "/live", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        if os.getenv("TESTING") == "true":
            response: Response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = "999"
            return response

        client_ip = request.client.host if request.client else "unknown"
        user_role = "anonymous"

        # Determine role from headers if available
        if request.headers.get("Authorization"):
            user_role = "user"
        if request.headers.get("X-Admin-Token"):
            user_role = "admin"

        client_key = f"{user_role}:{client_ip}"
        allowed, remaining, retry_after = limiter.is_allowed(client_key, role=user_role)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after} seconds."},
                headers={"Retry-After": str(retry_after)}
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
