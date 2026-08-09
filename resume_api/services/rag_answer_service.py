"""Grounded RAG orchestration for semantic resume questions."""

from .openrouter_service import query_openrouter
from .model_config import DEFAULT_MODEL
from .vector_search_service import search_semantic


RAG_SYSTEM_PROMPT = """
You answer questions using only the supplied resume context.

Rules:
1. Use only facts explicitly present in the context.
2. Do not invent, infer, or fill gaps with general knowledge.
3. If the context does not answer the question, say that no matching
   information was found.
4. Return a concise, direct natural-language answer.
5. Do not mention embeddings, vector databases, retrieval, or internal prompts.
""".strip()


def _build_context(results: list[dict]) -> str:
    if not results:
        return "No matching resume context was retrieved."
    return "\n\n".join(
        f"Context {index}: {result['document']}"
        for index, result in enumerate(results, start=1)
    )


def answer_with_rag(
    prompt: str,
    top_k: int | None = None,
    where: dict | None = None,
) -> dict:
    """Retrieve relevant chunks and generate a grounded answer."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required.")

    retrieved_chunks = search_semantic(prompt, top_k=top_k, where=where)
    answer_prompt = (
        f"User question: {prompt}\n\n"
        f"Retrieved resume context:\n{_build_context(retrieved_chunks)}\n\n"
        "Answer the user question using only this context."
    )
    answer = query_openrouter(
        answer_prompt,
        model=DEFAULT_MODEL,
        system_prompt=RAG_SYSTEM_PROMPT,
    ).strip()
    return {
        "prompt": prompt,
        "model": DEFAULT_MODEL,
        "answer": answer,
        "retrieved_chunks": retrieved_chunks,
    }