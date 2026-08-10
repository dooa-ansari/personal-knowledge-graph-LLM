"""Shared utility functions for the resume API."""

import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


def get_embedding_client() -> OpenAI:
    """Create an OpenAI-compatible client pointed at OpenRouter."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key or api_key == "your-openrouter-api-key-here":
        raise ValueError("OPENROUTER_API_KEY is not configured.")
    return OpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
    )