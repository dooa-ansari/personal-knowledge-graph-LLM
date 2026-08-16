"""
Production settings.

DEBUG=False, Swagger disabled, strict CSP, HSTS, Secure cookies.
All XSS and MitM protections enforced at max level.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = []  # Must be configured per deployment

# Middleware with security headers and session enforcement
MIDDLEWARE = [
    "core.middleware.SecurityHeadersMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.SessionEnforcerMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# Production security headers: strict CSP, no inline scripts
# ---------------------------------------------------------------------------
SECURITY_HEADERS = {
    "X-XSS-Protection": "1; mode=block",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Strict CSP: no unsafe-inline (Swagger disabled in prod anyway)
    "Content-Security-Policy": "default-src 'self'",
    # HSTS: enforce HTTPS for 1 year including subdomains
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
}

# ---------------------------------------------------------------------------
# MitM protections: HTTPS enforcement
# ---------------------------------------------------------------------------

# Cookies only sent over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Redirect all HTTP to HTTPS
SECURE_SSL_REDIRECT = True

# HTTP Strict Transport Security
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Disable Swagger in production
SWAGGER_ENABLED = False
