"""
Shared Django settings for all environments.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# OpenRouter API Configuration
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# RAG configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
CHROMA_PERSIST_PATH = os.getenv(
    "CHROMA_PERSIST_PATH", str(BASE_DIR / "data" / "chroma")
)
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "resume_chunks")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "2"))
CHROMA_ANONYMIZED_TELEMETRY = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-h%1+fp@78b79ff$k&m*1c49afrf%ex$cv!v329-_1t3_c5&sza",
)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_yasg",
    "core",
    "resume_api",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Shared security settings: XSS & MitM protections (always on)
# ---------------------------------------------------------------------------

# Prevent browser from MIME-sniffing (blocks XSS via MIME confusion)
SECURE_CONTENT_TYPE_NOSNIFF = True

# Legacy XSS filter (useful for older browsers)
SECURE_BROWSER_XSS_FILTER = True

# Session cookie inaccessible to JavaScript (prevents XSS cookie theft)
SESSION_COOKIE_HTTPONLY = True

# Strict SameSite: cookie only sent for same-site requests (blocks CSRF/MitM session riding)
SESSION_COOKIE_SAMESITE = "Strict"

# Session dies when browser closes (one-time session enforcement)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF cookie inaccessible to JavaScript
CSRF_COOKIE_HTTPONLY = True

# Strict SameSite for CSRF cookie too
CSRF_COOKIE_SAMESITE = "Strict"

# Clickjacking protection
X_FRAME_OPTIONS = "DENY"
