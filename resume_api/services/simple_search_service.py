"""
Simple one-shot knowledge graph search service.

This module implements a stateless, single-turn search flow:
1. Translate a natural language question into a SPARQL query (via OpenRouter).
2. Execute the SPARQL query against the RDF knowledge graph (via rdflib).
3. Convert the query results into a natural language answer (via OpenRouter).

Unlike the LangGraph-based service, this has no conversation context,
no session IDs, and no persisted state — each call is independent.
"""

from django.conf import settings

from ..prompts import (
    NATURAL_LANGUAGE_SYSTEM_PROMPT,
    SPARQL_SYSTEM_PROMPT,
    build_results_prompt,
)
from .model_config import DEFAULT_MODEL
from .openrouter_service import query_openrouter
from .sparql_service import execute_sparql_query, validate_sparql_query

MAX_SPARQL_GENERATION_ATTEMPTS = 2

def search_simple(prompt: str) -> dict:
    """
    Perform a single, stateless knowledge graph search.

    Args:
        prompt: The user's natural language question.

    Returns:
        A dict containing:
        - prompt: The user's prompt
        - model: The model used
        - sparql_query: The generated SPARQL query
        - query_results: The raw SPARQL query results
        - answer: The natural language answer

    Raises:
        ValueError: If the API key is not configured.
        FileNotFoundError: If the RDF file doesn't exist.
        Exception: If the search flow fails.
    """
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your-openrouter-api-key-here":
        raise ValueError(
            "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file."
        )

    # Step 1: Translate the natural language question into a SPARQL query
    generation_prompt = prompt
    last_error = None
    for attempt in range(1, MAX_SPARQL_GENERATION_ATTEMPTS + 1):
        sparql_query = query_openrouter(
            generation_prompt,
            model=DEFAULT_MODEL,
            system_prompt=SPARQL_SYSTEM_PROMPT,
        ).strip()

        try:
            validate_sparql_query(sparql_query)
            break
        except Exception as exc:
            last_error = exc
            if attempt == MAX_SPARQL_GENERATION_ATTEMPTS:
                raise ValueError(
                    f"Generated SPARQL query remained invalid after {attempt} attempts: {exc}"
                ) from exc
            generation_prompt = (
                f"{prompt}\n\nThe previous SPARQL query was invalid. "
                f"Parser error: {exc}\n"
                "Regenerate the query. Return only raw SPARQL without Markdown fences."
            )

    print(
        f"\n===== Generated SPARQL query (stateless search) =====\n{sparql_query}\n===== End SPARQL query =====\n",
        flush=True,
    )

    # Step 2: Execute the SPARQL query against the RDF knowledge graph
    query_results = execute_sparql_query(sparql_query)

    # Step 3: Convert the query results into a natural language answer
    results_prompt = build_results_prompt(prompt, query_results)
    answer = query_openrouter(
        results_prompt,
        model=DEFAULT_MODEL,
        system_prompt=NATURAL_LANGUAGE_SYSTEM_PROMPT,
    ).strip()

    return {
        "prompt": prompt,
        "model": DEFAULT_MODEL,
        "sparql_query": sparql_query,
        "query_results": query_results,
        "answer": answer,
    }