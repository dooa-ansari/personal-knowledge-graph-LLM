"""Semantic retrieval from the persisted ChromaDB resume collection."""

import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings as ChromaSettings
from django.conf import settings
from openai import OpenAI


def _embedding_client() -> OpenAI:
    """Create an OpenAI-compatible client pointed at OpenRouter."""
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your-openrouter-api-key-here":
        raise ValueError("OPENROUTER_API_KEY is not configured.")
    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )


def _collection():
    """Open the persisted collection without creating a missing index."""
    client = chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        return client.get_collection(settings.RAG_COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "RAG index is not available. Run `python3 manage.py reindex_rag` first."
        ) from exc


def search_semantic(query: str, top_k: int | None = None, where: dict | None = None) -> list[dict]:
    """Return the nearest resume chunks for a natural-language query.

    Args:
        query: User's semantic search text.
        top_k: Number of results, defaulting to ``RAG_TOP_K``.
        where: Optional Chroma metadata filter, such as
            ``{"entity_type": "ProfessionalExperience"}``.
    """
    query = query.strip()
    if not query:
        raise ValueError("Search query is required.")

    limit = top_k if top_k is not None else settings.RAG_TOP_K
    if limit < 1:
        raise ValueError("top_k must be greater than zero.")

    embedding_response = _embedding_client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[query],
    )
    query_embedding = embedding_response.data[0].embedding
    result = _collection().query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {
            "document": document,
            "metadata": metadata or {},
            "distance": distance,
            "score": 1 / (1 + distance) if distance is not None else None,
        }
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]