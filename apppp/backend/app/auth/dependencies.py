"""Authentication dependencies for FastAPI.

Verifies Firebase ID tokens and provides the current user.
In development mode, allows a bypass for testing (with logged warning).
"""

import logging
import uuid

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

    # Custom JWT token verification
    try:
        import jwt
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        pass

    # Firebase token verification fallback
    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception as e:
        logger.error("Token verification failed", exc_info=e)
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    uid: str | None = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get or create user from verified auth token."""
    if uid is None:
        return None

    if db is None:
        return User(
            id=str(uuid.uuid4()),
            auth_provider_id=uid,
            email=f"{uid}@biopolymer.ai" if "@" not in uid else uid,
            display_name=uid,
            role="user",
        )

    result = await db.execute(
        select(User).where(User.auth_provider_id == uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        email = None
        display_name = None
        try:
            from firebase_admin import auth as firebase_auth
            fb_user = firebase_auth.get_user(uid)
            email = fb_user.email
            display_name = fb_user.display_name or (email.split("@")[0] if email else None)
        except Exception:
            pass

        # Auto-create user on first login
        user = User(
            auth_provider_id=uid,
            email=email,
            display_name=display_name,
            role="user"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif not user.email or not user.display_name:
        try:
            from firebase_admin import auth as firebase_auth
            fb_user = firebase_auth.get_user(uid)
            updated = False
            if not user.email and fb_user.email:
                user.email = fb_user.email
                updated = True
            if not user.display_name and fb_user.display_name:
                user.display_name = fb_user.display_name
                updated = True
            if updated:
                await db.commit()
        except Exception:
            pass

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
