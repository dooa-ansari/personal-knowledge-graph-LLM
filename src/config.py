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
# OpenRouter API
# ---------------------------------------------------------------------------
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ---------------------------------------------------------------------------
# RAG / ChromaDB
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
CHROMA_PERSIST_PATH = os.getenv(
    "CHROMA_PERSIST_PATH", str(PROJECT_ROOT / "chroma")
)
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "resume_chunks")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "2"))

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-h%1+fp@78b79ff$k&m*1c49afrf%ex$cv!v329-_1t3_c5&sza",
)