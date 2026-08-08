"""FastAPI application entry point.

Security hardening applied here:
- CORS restricted to origins declared in settings.effective_cors_origins
- Security response headers injected via middleware (HSTS, CSP, X-Frame-Options, etc.)
- Interactive docs (/docs, /redoc) disabled in production
- Rate limiting via slowapi
- Structured /health endpoint with version and environment info

Request lifecycle logging
--------------------------
Every request is traced end-to-end:

  → [req_id] METHOD /path  (request received)
  ← [req_id] METHOD /path  status=200  elapsed_ms=42.3  (response sent)
  ⚠ [req_id] METHOD /path  SLOW REQUEST  elapsed_ms=6123.4  (> SLOW_REQUEST_THRESHOLD_MS)

The X-Request-ID header is echoed back to the client and the Android app logs
it so any timeout can be correlated with a specific server-side trace entry
without guessing which request caused the problem.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.database import create_all_tables
from app.core.security import RateLimitMiddleware

logger = logging.getLogger(__name__)

# Requests slower than this will be logged at WARNING level so they surface
# immediately in any log aggregation tool (CloudWatch, Datadog, etc.).
SLOW_REQUEST_THRESHOLD_MS: float = 5_000.0

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security-related HTTP response headers to every response.

    These headers harden the API against common web vulnerabilities even
    when the API is consumed by mobile clients (browsers also benefit).

    SSE streams MUST NOT have Cache-Control: no-store applied — that header
    tells nginx and other reverse proxies to buffer the full body before
    forwarding, which defeats streaming entirely and causes "Server took too
    long to respond" errors on the client.  The SSE endpoint sets its own
    Cache-Control: no-cache + X-Accel-Buffering: no headers; this middleware
    must not overwrite them.
    """

    # Content-Type prefix that identifies SSE responses.
    _SSE_CONTENT_TYPE = "text/event-stream"

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Determine whether this is an SSE (streaming) response.
        # StreamingResponse sets the content-type before the middleware sees it.
        is_sse = response.headers.get("content-type", "").startswith(
            self._SSE_CONTENT_TYPE
        )

        # Prevent browsers from MIME-sniffing the content type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Deny framing entirely (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Restrict referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if is_sse:
            # SSE streams must NOT have Cache-Control: no-store.
            # The endpoint already sets Cache-Control: no-cache and
            # X-Accel-Buffering: no — preserve those so nginx/proxies
            # forward each frame immediately without buffering.
            # Do NOT set Pragma: no-cache either — it causes the same
            # buffering problem with some proxy implementations.
            pass
        else:
            # Standard JSON / non-streaming responses: disable caching.
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        # Content-Security-Policy — APIs don't serve HTML, but this prevents
        # browsers from executing injected scripts if they somehow render a
        # response body.
        response.headers["Content-Security-Policy"] = "default-src 'none'"

        # Permissions Policy — disable browser features the API will never use
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS — only set on HTTPS (production/staging).  Setting it on plain
        # HTTP causes browsers to refuse future plain-HTTP connections.
        if settings.is_production or settings.APP_ENV == "staging":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response


# ---------------------------------------------------------------------------
# Request ID / correlation + lifecycle logging middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attaches a unique X-Request-ID to every request and response, and emits
    structured log lines that trace the complete request lifecycle.

    Log format
    ----------
    Incoming request::

        → [<req_id>] GET /api/v1/materials/sync  client=10.0.2.2

    Completed response::

        ← [<req_id>] GET /api/v1/materials/sync  status=200  elapsed_ms=38.4

    Slow-request warning (> SLOW_REQUEST_THRESHOLD_MS)::

        ⚠ SLOW [<req_id>] GET /api/v1/materials/sync  status=200  elapsed_ms=6120.7

    The Android client sends X-Request-ID (added in NetworkModule) so the same
    ID appears in both Logcat and the server log, enabling exact correlation
    without any guesswork.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Honour a client-supplied ID (Android sends one); generate if absent.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        client_host = request.client.host if request.client else "unknown"

        # ── Incoming ──────────────────────────────────────────────────────
        logger.info(
            "→ [%s] %s %s  client=%s",
            request_id,
            request.method,
            request.url.path,
            client_host,
        )

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        # ── Completed ─────────────────────────────────────────────────────
        is_slow = elapsed_ms > SLOW_REQUEST_THRESHOLD_MS
        log_level = logging.WARNING if is_slow else logging.INFO
        prefix = f"⚠ SLOW [{request_id}]" if is_slow else f"← [{request_id}]"

        logger.log(
            log_level,
            "%s %s %s  status=%d  elapsed_ms=%.1f",
            prefix,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        return response


# ---------------------------------------------------------------------------
# App factory / lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import models so SQLAlchemy metadata is populated before create_all
    import app.models.user  # noqa: F401
    import app.models.project  # noqa: F401
    from app.services.model_manager import ModelManager

    logger.info(
        "Starting BioPolymer API | env=%s debug=%s",
        settings.APP_ENV,
        settings.APP_DEBUG,
    )
    logger.info("CORS origins: %s", settings.effective_cors_origins)

    # Load active pre-trained model from registry (never train at startup)
    try:
        loaded = ModelManager.load_latest()
        if loaded:
            logger.info("Active production AI model successfully loaded into memory.")
        else:
            logger.warning("No pre-trained model registry artifact found.")
    except Exception as exc:
        logger.error("Failed to load model registry: %s", exc)

    # Create tables that do not yet exist (idempotent)
    try:
        await create_all_tables()
        logger.info("Database tables verified/created.")
        from app.core.schema_validator import validate_database_schema
        validate_database_schema()
    except Exception as exc:
        logger.error("Failed to create/validate database tables: %s", exc)
    yield
    logger.info("Shutting down BioPolymer API")


app = FastAPI(
    title="BioPolymer AI Screening API",
    description=(
        "AI-powered decision-support API that recommends natural biopolymers "
        "for biomedical packaging applications."
    ),
    version="0.1.0",
    # Disable interactive docs in production to reduce attack surface.
    docs_url="/docs" if settings.openapi_enabled else None,
    redoc_url="/redoc" if settings.openapi_enabled else None,
    openapi_url="/openapi.json" if settings.openapi_enabled else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware — order matters: outermost middleware runs first on request and
# last on response.  RequestID must wrap everything so the ID is present on
# error responses too.
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Request ID (outermost — applied to every request before any other logic)
app.add_middleware(RequestIDMiddleware)

# 2. Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# 3. Security headers (applied to every response)
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS (must come after security headers so CORS preflight responses also
#    carry the security headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    # Expose these headers so clients can read them
    expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
)

# ---------------------------------------------------------------------------
# Global exception handler — never leak stack traces to clients
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception | request_id=%s path=%s",
        request_id,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(api_router)


START_TIME = time.time()


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """Enhanced health check endpoint.

    Returns 200 with service, database, and system status information.
    """
    from app.database import get_db
    mysql_connected = False
    try:
        from sqlalchemy import text
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            mysql_connected = True
            break
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")

    uptime_sec = round(time.time() - START_TIME, 1)

    return {
        "status": "healthy" if mysql_connected else "degraded",
        "service": "BioPolymer AI Screening API",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "mysql_connected": mysql_connected,
        "uptime_seconds": uptime_sec,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": getattr(request.state, "request_id", None),
    }


from fastapi.responses import JSONResponse, RedirectResponse

@app.get("/materials", include_in_schema=False)
async def redirect_materials(request: Request):
    query_str = f"?{request.query_params}" if request.query_params else ""
    return RedirectResponse(url=f"/api/v1/materials{query_str}", status_code=307)


@app.post("/screen", include_in_schema=False)
async def redirect_screen():
    return RedirectResponse(url="/api/v1/screening", status_code=307)




@app.get("/", tags=["Root"])
async def root():
    """API root — returns service metadata."""
    return {
        "app": "BioPolymer AI Screening API",
        "version": "0.1.0",
        **({"docs": "/docs"} if settings.openapi_enabled else {}),
        "health": "/health",
        "materials": "/materials",
        "screen": "/screen",
        "api_v1": "/api/v1",
    }

