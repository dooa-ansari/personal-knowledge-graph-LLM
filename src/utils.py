"""
Shared client factories for ChromaDB and OpenAI-compatible embeddings.
"""

import logging
import os
from typing import Any

import redis

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from openai.types import CreateEmbeddingResponse

from . import config

logger = logging.getLogger(__name__)


def require_api_key() -> str:
    """Validate that the OpenRouter API key is configured. Returns the key."""
    api_key = config.OPENROUTER_API_KEY
    if not api_key or api_key == "your-openrouter-api-key-here":
        raise ValueError(
            "OPENROUTER_API_KEY is not configured. Set it in your .env file."
        )
    return api_key


def get_chroma_client() -> ClientAPI:
    """Create a ChromaDB PersistentClient with telemetry disabled."""
    return chromadb.PersistentClient(
        path=config.CHROMA_PERSIST_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_embedding_client() -> OpenAI:
    """Create an OpenAI-compatible client pointed at OpenRouter."""
    return OpenAI(
        api_key=require_api_key(),
        base_url=config.OPENROUTER_BASE_URL,
    )


def create_embeddings(texts: list[str]) -> CreateEmbeddingResponse:
    """Create vector embeddings for one or more texts."""
    return get_embedding_client().embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=texts,
    )


def get_redis_client() -> Any:
    """Create a Redis client for session-backed chat history."""
    return redis.from_url(config.REDIS_URL, decode_responses=True)
