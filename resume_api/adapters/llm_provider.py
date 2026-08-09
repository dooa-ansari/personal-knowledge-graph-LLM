"""Concrete LLM provider adapter wrapping the existing OpenRouter service."""

from resume_api.ports.repositories import LLMProvider
from resume_api.services.openrouter_service import query_openrouter
from resume_api.services.model_config import DEFAULT_MODEL


class OpenRouterLLMProvider(LLMProvider):
    """Adapter that wraps the existing OpenRouter service as an LLMProvider."""

    def query(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system_prompt: str | None = None,
    ) -> str:
        return query_openrouter(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
        )