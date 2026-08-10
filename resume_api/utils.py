"""Shared utility functions for the resume API."""

import logging
import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings as ChromaSettings
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


def require_api_key() -> str:
    """Validate that the OpenRouter API key is configured.  Returns the key."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key or api_key == "your-openrouter-api-key-here":
        raise ValueError(
            "OPENROUTER_API_KEY is not configured. Set it in your .env file."
        )
    return api_key


def get_chroma_client() -> chromadb.PersistentClient:
    """Create a ChromaDB PersistentClient with telemetry disabled."""
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_embedding_client() -> OpenAI:
    """Create an OpenAI-compatible client pointed at OpenRouter."""
    return OpenAI(
        api_key=require_api_key(),
        base_url=settings.OPENROUTER_BASE_URL,
    )


def create_embeddings(texts: list[str]):
    """Create vector embeddings for one or more texts."""
    return get_embedding_client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )