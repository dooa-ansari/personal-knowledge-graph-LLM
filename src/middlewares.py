"""FastAPI dependencies — session enforcement and API key validation."""

import uuid
import logging

from fastapi import Cookie, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src import config

logger = logging.getLogger(__name__)

SESSION_COOKIE = "session_id"
SESSION_EXEMPT_PATHS = {"/docs", "/openapi.json"}


# ---------------------------------------------------------------------------
# Middleware — auto-create anonymous session cookie on first visit
# ---------------------------------------------------------------------------

def _is_valid_session_id(session_id: str) -> bool:
    if not session_id:
        return False
    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False


class SessionEnforcerMiddleware(BaseHTTPMiddleware):
    """Ensure every visitor has a valid session cookie. Rotate if invalid/missing."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        for exempt in SESSION_EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        incoming_session_id = request.cookies.get(SESSION_COOKIE, "")
        if _is_valid_session_id(incoming_session_id):
            session_id = incoming_session_id
        else:
            session_id = uuid.uuid4().hex
            logger.debug("Created anonymous session: %s", session_id)

        request.state.session_id = session_id
        response = await call_next(request)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            httponly=True,
            # Browsers reject SameSite=None without Secure. Cross-site setups
            # (e.g. Vercel/GitHub Pages frontend -> UpCloud API) need None+Secure,
            # which requires the API to serve over HTTPS (SESSION_COOKIE_SECURE=true).
            samesite="none" if config.SESSION_COOKIE_SECURE else "strict",
            secure=config.SESSION_COOKIE_SECURE,
            max_age=config.SESSION_TTL_SECONDS,
        )
        return response


# ---------------------------------------------------------------------------
# Dependency — require a valid session cookie
# ---------------------------------------------------------------------------

def get_session_id(
    request: Request,
    session_id: str = Cookie(default="", alias=SESSION_COOKIE),
) -> str:
    """FastAPI dependency: extract and validate the session cookie."""
    state_session_id = getattr(request.state, "session_id", "")
    if _is_valid_session_id(state_session_id):
        return state_session_id
    if _is_valid_session_id(session_id):
        return session_id
    raise HTTPException(status_code=403, detail="No valid session found. Please refresh the page.")


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