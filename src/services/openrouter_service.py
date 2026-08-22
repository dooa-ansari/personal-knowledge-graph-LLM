"""
OpenRouter API service for interacting with language models.
"""

import logging

import requests

from src import config
from src.clients import require_api_key
from src.services.model_config import DEFAULT_MODEL

logger = logging.getLogger(__name__)


def query_openrouter(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = None,
) -> str:
    """Send a prompt to OpenRouter API and return the model's response."""
    api_key = require_api_key()
    base_url = config.OPENROUTER_BASE_URL

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages}

    logger.info("LLM call model=%s prompt_len=%d has_system=%s", model, len(prompt), bool(system_prompt))
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    logger.info("LLM response model=%s response_len=%d", model, len(content))
    return content