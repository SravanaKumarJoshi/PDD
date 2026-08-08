"""Authentication dependencies for FastAPI.

Verifies Firebase ID tokens and provides the current user.
In development mode, allows a bypass for testing (with logged warning).
"""

import logging

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)


def _extract_bearer_token(authorization: str | None) -> str:
    """Safely extract the bearer token from the Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication failed")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication failed")
    return parts[1]


async def get_current_user_id(
    authorization: str = Header(None),
) -> str | None:
    """Extract and verify user ID from Authorization header.

    In production, this verifies a Firebase ID token.
    In development, accepts 'Bearer dev-<uid>' for testing (logs a warning).
    """
    token = _extract_bearer_token(authorization)

    # Development bypass — only allowed when APP_ENV is explicitly "development"
    if token.startswith("dev-"):
        if settings.APP_ENV == "development":
            uid = token[4:]
            logger.warning("DEV AUTH BYPASS used for uid=%s", uid)
            return uid
        # Reject dev tokens outside development mode
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Firebase token verification
    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        # Initialize Firebase Admin SDK if not already done
        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception as e:
        # Log full error server-side; return generic message to client
        logger.error("Token verification failed", exc_info=e)
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    uid: str | None = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get or create user from verified auth token."""
    if uid is None:
        return None

    result = await db.execute(
        select(User).where(User.auth_provider_id == uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create user on first login
        user = User(auth_provider_id=uid)
        db.add(user)
        await db.flush()

    return user


async def require_auth(
    user: User | None = Depends(get_current_user),
) -> User:
    """Require authenticated user — raises 401 if not logged in."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


async def require_admin(
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> bool:
    """Check admin token for admin-only endpoints."""
    if not admin_token or admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return True
