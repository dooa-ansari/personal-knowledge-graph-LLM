"""FastAPI dependencies — session enforcement and API key validation."""

import uuid
import logging

from fastapi import Cookie, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src import config

logger = logging.getLogger(__name__)

SESSION_COOKIE = "session_id"
SESSION_EXEMPT_PATHS = {"/docs", "/openapi.json"}


# ---------------------------------------------------------------------------
# Middleware — auto-create anonymous session cookie on first visit
# ---------------------------------------------------------------------------

class SessionEnforcerMiddleware(BaseHTTPMiddleware):
    """Ensure every visitor has a session cookie. Creates one if missing."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        for exempt in SESSION_EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        response = await call_next(request)
        if SESSION_COOKIE not in request.cookies:
            session_id = uuid.uuid4().hex
            response.set_cookie(
                key=SESSION_COOKIE,
                value=session_id,
                httponly=True,
                samesite="strict",
                max_age=None,  # browser-session cookie
            )
            logger.debug("Created anonymous session: %s", session_id)
        return response


# ---------------------------------------------------------------------------
# Dependency — require a valid session cookie
# ---------------------------------------------------------------------------

def get_session_id(session_id: str = Cookie(default="", alias=SESSION_COOKIE)) -> str:
    """FastAPI dependency: extract and validate the session cookie."""
    if not session_id:
        raise HTTPException(status_code=403, detail="No valid session found. Please refresh the page.")
    return session_id


# ---------------------------------------------------------------------------
# Dependency — validate API key is configured
# ---------------------------------------------------------------------------

def require_api_key_dep() -> str:
    """FastAPI dependency: ensure OpenRouter API key is set."""
    api_key = config.OPENROUTER_API_KEY
    if not api_key or api_key == "your-openrouter-api-key-here":
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY is not configured.",
        )
    return api_key