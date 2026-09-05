"""
Central configuration — single source of truth for all settings.
Reads from environment variables with sensible defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from the project root
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# OpenRouter API & Models
# ---------------------------------------------------------------------------
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "inclusionai/ling-3.0-flash")

# ---------------------------------------------------------------------------
# RAG / ChromaDB
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
CHROMA_PERSIST_PATH = os.getenv(
    "CHROMA_PERSIST_PATH", str(PROJECT_ROOT / "chroma")
)
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "resume_chunks")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "2"))
RAG_SEARCH_RATE_LIMIT = os.getenv("RAG_SEARCH_RATE_LIMIT", "30/minute")

def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "900"))
SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), False)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]