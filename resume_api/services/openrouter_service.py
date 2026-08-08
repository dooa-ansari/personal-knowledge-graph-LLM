"""
OpenRouter API service for interacting with language models.
"""

import requests
from django.conf import settings

from .model_config import DEFAULT_MODEL


def query_openrouter(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = None,
) -> str:
    """
    Send a prompt to OpenRouter API and return the model's response.

    Args:
        prompt: The user prompt to send to the model
        model: The model identifier to use (defaults to the central DEFAULT_MODEL)
        system_prompt: An optional system prompt to instruct the model's behavior

    Returns:
        The model's response text

    Raises:
        ValueError: If the API key is not configured
        requests.RequestException: If the API call fails
    """
    api_key = settings.OPENROUTER_API_KEY
    base_url = settings.OPENROUTER_BASE_URL

    if not api_key or api_key == "your-openrouter-api-key-here":
        raise ValueError("OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file.")

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Build messages list with optional system prompt
    messages = []
    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )
    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    payload = {
        "model": model,
        "messages": messages,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]