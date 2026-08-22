"""Simplified session-aware semantic RAG workflow."""

import logging
from typing import TypedDict, cast

from src import config
from src.clients import create_embeddings, get_chroma_client
from src.services.model_config import DEFAULT_MODEL
from src.services.openrouter_service import query_openrouter

logger = logging.getLogger(__name__)


RAG_CONVERSATION_SYSTEM_PROMPT = """
You answer questions using only the supplied resume context and conversation.
Use conversation history to resolve references such as "there", "that role",
or "what about next?", but do not treat history as resume facts unless those
facts are also present in the retrieved context.
If the retrieved context does not answer the question, say so clearly.
Return only a concise natural-language answer.
""".strip()


_session_store: dict[str, list[dict[str, str]]] = {}


class RetrievedChunk(TypedDict):
    document: str
    metadata: dict[str, str]
    distance: float | None
    score: float | None


class RagResult(TypedDict):
    prompt: str
    session_id: str
    model: str
    retrieval_query: str
    answer: str
    retrieved_chunks: list[RetrievedChunk]


def _rewrite_query(latest_question: str, history: str) -> str:
    rewrite_prompt = (
        "Rewrite the current question as one standalone semantic search query "
        "for a resume database. Resolve pronouns and references using the "
        "conversation history. Preserve the user's intent. Return only the "
        "rewritten query, with no explanation.\n\n"
        f"Conversation history:\n{history or '(none)'}\n\n"
        f"Current question:\n{latest_question}"
    )
    rewritten = query_openrouter(
        prompt=rewrite_prompt,
        model=DEFAULT_MODEL,
        system_prompt="You rewrite questions into standalone search queries.",
    ).strip()
    return rewritten or latest_question


def _retrieve(query: str) -> list[RetrievedChunk]:
    """Retrieve relevant chunks from ChromaDB."""
    query = query.strip()
    if not query:
        raise ValueError("Search query is required.")

    try:
        collection = get_chroma_client().get_collection(config.RAG_COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "RAG index is not available. Run `uv run python -m scripts.reindex` first."
        ) from exc

    embedding_response = create_embeddings([query])
    query_embedding = embedding_response.data[0].embedding
    result: object = collection.query(
        query_embeddings=[query_embedding],
        n_results=config.RAG_TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    result_dict: dict[str, object] = cast(dict[str, object], cast(object, result))
    raw_docs: object = result_dict["documents"]
    raw_meta: object = result_dict["metadatas"]
    raw_dist: object = result_dict["distances"]
    documents: list[str] = cast(list[str], cast(list[object], raw_docs)[0])
    metadatas: list[dict[str, str]] = cast(list[dict[str, str]], cast(list[object], raw_meta)[0])
    distances: list[float | None] = cast(list[float | None], cast(list[object], raw_dist)[0])
    return [
        {
            "document": document,
            "metadata": metadata or {},
            "distance": distance,
            "score": 1 / (1 + distance) if distance is not None else None,
        }
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]


def _answer(question: str, history: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"Context {index}: {chunk['document']}"
        for index, chunk in enumerate(chunks, start=1)
    ) or "No matching resume context was retrieved."

    prompt = (
        f"Conversation history:\n{history or '(none)'}\n\n"
        f"Current question: {question}\n\n"
        f"Retrieved resume context:\n{context}\n\n"
        "Answer using only the retrieved context."
    )
    return query_openrouter(
        prompt,
        model=DEFAULT_MODEL,
        system_prompt=RAG_CONVERSATION_SYSTEM_PROMPT,
    ).strip()


def search_rag(session_id: str, prompt: str) -> RagResult:
    if not session_id:
        raise ValueError("Session ID is required.")
    if not prompt.strip():
        raise ValueError("Prompt is required.")

    messages = _session_store.get(session_id, [])
    history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in messages
    )

    logger.info(
        "RAG session=%s prompt=%.60s history_len=%d",
        session_id, prompt, len(messages),
    )

    retrieval_query = _rewrite_query(prompt.strip(), history)
    retrieved_chunks = _retrieve(retrieval_query)
    logger.info(
        "RAG session=%s retrieved=%d query=%.60s",
        session_id, len(retrieved_chunks), retrieval_query,
    )

    answer = _answer(prompt.strip(), history, retrieved_chunks)

    messages.append({"role": "user", "content": prompt.strip()})
    messages.append({"role": "assistant", "content": answer})
    _session_store[session_id] = messages

    return {
        "prompt": prompt.strip(),
        "session_id": session_id,
        "model": DEFAULT_MODEL,
        "retrieval_query": retrieval_query,
        "answer": answer,
        "retrieved_chunks": retrieved_chunks,
    }