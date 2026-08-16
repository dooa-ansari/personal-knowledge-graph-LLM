"""
DRF permission classes for anonymous session-based authorization.
"""
import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsSessionValid(BasePermission):
    """Allow access only if the request carries a valid anonymous session.

    The session is created automatically by SessionEnforcerMiddleware on the
    first request, so this effectively means: "every visitor must have a
    browser session cookie that the server recognizes."

    Rejected requests receive HTTP 403 with a descriptive error.
    """

    def has_permission(self, request, view):
        session_key = request.session.session_key

        if not session_key:
            logger.warning("Blocked request: no session key")
            return False

        if not request.session.exists(session_key):
            logger.warning("Blocked request: invalid session %s", session_key)
            return False

        return True
