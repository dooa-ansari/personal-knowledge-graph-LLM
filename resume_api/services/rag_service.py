"""Simplified session-aware semantic RAG workflow — no LangGraph needed."""

import logging
from typing import TypedDict

from resume_api.services.model_config import DEFAULT_MODEL
from resume_api.services.openrouter_service import query_openrouter
from resume_api.services.vector_repository import ChromaVectorRepository

logger = logging.getLogger(__name__)


RAG_CONVERSATION_SYSTEM_PROMPT = """
You answer questions using only the supplied resume context and conversation.
Use conversation history to resolve references such as "there", "that role",
or "what about next?", but do not treat history as resume facts unless those
facts are also present in the retrieved context.
If the retrieved context does not answer the question, say so clearly.
Return only a concise natural-language answer.
""".strip()


# In-memory session store. For production, replace with Django cache or DB.
_session_store: dict[str, list] = {}


class RagResult(TypedDict):
    prompt: str
    session_id: str
    model: str
    retrieval_query: str
    answer: str
    retrieved_chunks: list[dict]


def _rewrite_query(latest_question: str, history: str) -> str:
    """Rewrite the current question as a standalone search query."""
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


def _retrieve(query: str) -> list[dict]:
    """Retrieve relevant chunks from the vector store."""
    repo = ChromaVectorRepository()
    return repo.search_semantic(query)


def _answer(question: str, history: str, chunks: list[dict]) -> str:
    """Generate a grounded answer using retrieved chunks."""
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


def search_rag(session_id: str, prompt: str) -> dict:
    """Run a session-aware RAG turn and return answer plus retrieved chunks."""
    if not session_id:
        raise ValueError("Session ID is required.")
    if not prompt.strip():
        raise ValueError("Prompt is required.")

    # Get or initialize session history
    messages = _session_store.get(session_id, [])
    history = "\n".join(
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    )

    logger.info(
        "RAG session=%s prompt=%.60s history_len=%d",
        session_id, prompt, len(messages),
    )

    # Step 1: Rewrite query contextually
    retrieval_query = _rewrite_query(prompt.strip(), history)

    # Step 2: Retrieve relevant chunks
    retrieved_chunks = _retrieve(retrieval_query)
    logger.info(
        "RAG session=%s retrieved=%d query=%.60s",
        session_id, len(retrieved_chunks), retrieval_query,
    )

    # Step 3: Generate grounded answer
    answer = _answer(prompt.strip(), history, retrieved_chunks)

    # Store in history
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