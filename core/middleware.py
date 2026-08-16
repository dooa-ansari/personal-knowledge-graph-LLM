"""
Custom middleware for security headers and anonymous session enforcement.
"""
import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Paths excluded from session enforcement (public docs, Swagger, admin)
SESSION_EXEMPT_PATHS = {
    "/swagger",
    "/admin",
}


class SecurityHeadersMiddleware:
    """Inject security headers into every response.

    Headers configured via settings.SECURITY_HEADERS dict.
    Provides XSS, MitM, and MIME-sniffing protections.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        headers = getattr(settings, "SECURITY_HEADERS", {})
        for header_name, header_value in headers.items():
            response[header_name] = header_value
        return response


class SessionEnforcerMiddleware:
    """Ensure every visitor has an active anonymous session.

    On first visit, a new browser-session cookie is created automatically.
    The session is server-side only (HttpOnly cookie), expires on browser close.

    URLs matching SESSION_EXEMPT_PATHS are not enforced.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip session enforcement for exempt paths
        for exempt in SESSION_EXEMPT_PATHS:
            if path.startswith(exempt):
                return self.get_response(request)

        # Force-create a session if one does not exist yet
        if not request.session.session_key:
            request.session.save()
            logger.debug("Created anonymous session: %s", request.session.session_key)

        return self.get_response(request)
