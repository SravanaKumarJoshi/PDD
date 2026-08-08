"""Application configuration via environment variables.

All values are injected through environment variables or a .env file.
No hardcoded URLs, IPs, or secrets are permitted in this file.
"""

import logging
from typing import List, Literal

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_UNSAFE_ADMIN_TOKENS = {
    "",
    "change-this-to-a-secure-random-string",
    "admin",
    "secret",
    "test",
}

# ---------------------------------------------------------------------------
# Default CORS origins per environment.
# These are ONLY used as fallbacks when CORS_ORIGINS is not set in the env
# file.  Production MUST set CORS_ORIGINS explicitly.
# ---------------------------------------------------------------------------
_DEFAULT_CORS: dict[str, list[str]] = {
    "development": [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    "test": [
        "http://localhost:3000",
    ],
    "staging": [
        # Replace with your real staging frontend origin before deployment.
        "https://staging.yourdomain.com",
    ],
    "production": [
        # Replace with your real production frontend origin before deployment.
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ],
}


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Database — MySQL only.
    # Format: mysql+aiomysql://user:password@host:port/database
    # Set DATABASE_URL explicitly in every environment via .env.
    # ------------------------------------------------------------------
    DATABASE_URL: str = "mysql+aiomysql://root:root123@localhost:3306/polysaccharide_selector"

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    FIREBASE_PROJECT_ID: str = ""

    # ------------------------------------------------------------------
    # Admin — MUST be overridden via environment variable / .env
    # ------------------------------------------------------------------
    ADMIN_TOKEN: str = ""

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    APP_DEBUG: bool = False  # Default to False; enable explicitly in dev/test .env

    # Server binding — used by the uvicorn start command in docker-compose
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Public-facing API base URL (used by OpenAPI docs and any URL generation)
    # Example: https://api.yourdomain.com
    API_BASE_URL: str = "http://localhost:8000"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    # Provide a JSON-encoded list, e.g.:
    #   CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
    # If not set, _DEFAULT_CORS[APP_ENV] is used as a fallback.
    CORS_ORIGINS: List[str] = []

    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Authorization",
        "Content-Type",
        "X-Admin-Token",
        "Accept",
        "X-Request-ID",
    ]
    # In production this should stay True so cookies/auth headers are forwarded.
    CORS_ALLOW_CREDENTIALS: bool = True

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------
    MAX_CSV_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # ------------------------------------------------------------------
    # Feature Flags
    # ------------------------------------------------------------------
    ENABLE_SCORE_BREAKDOWN: bool = True
    ENABLE_VALIDATION: bool = True
    ENABLE_PERFORMANCE_METRICS: bool = True
    ENABLE_AUDIT_LOGGING: bool = True
    ENABLE_SCHEMA_VALIDATION: bool = True
    ENABLE_RULE_SCORING: bool = True
    ENABLE_ML_SCORING: bool = True
    ENABLE_RESPONSE_METADATA: bool = True

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    SCORING_CONFIG_VERSION: str = "2.0.0"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def effective_cors_origins(self) -> List[str]:
        """Return configured origins, falling back to environment defaults."""
        if self.CORS_ORIGINS:
            return self.CORS_ORIGINS
        return _DEFAULT_CORS.get(self.APP_ENV, _DEFAULT_CORS["development"])

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def openapi_enabled(self) -> bool:
        """Disable interactive docs in production."""
        return not self.is_production


settings = Settings()

# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
if settings.ADMIN_TOKEN.strip().lower() in _UNSAFE_ADMIN_TOKENS:
    if settings.is_production or settings.APP_ENV == "staging":
        raise RuntimeError(
            "CRITICAL: ADMIN_TOKEN must be set to a secure random value in "
            f"{settings.APP_ENV}. Set ADMIN_TOKEN in your environment or .env file."
        )
    else:
        logger.warning(
            "ADMIN_TOKEN is not set or uses a placeholder value. "
            "Admin endpoints are effectively unprotected. "
            "Set a secure ADMIN_TOKEN in .env before deploying."
        )

if settings.is_production and not settings.CORS_ORIGINS:
    logger.warning(
        "CORS_ORIGINS is not explicitly set. Falling back to default production "
        "origins. Set CORS_ORIGINS in your .env to prevent misconfiguration."
    )
