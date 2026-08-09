"""Use case for session-aware semantic RAG search."""

from resume_api.ports.repositories import LLMProvider, VectorRepository
from resume_api.services.model_config import DEFAULT_MODEL


RAG_CONVERSATION_SYSTEM_PROMPT = """
You answer questions using only the supplied resume context and conversation.
Use conversation history to resolve references such as "there", "that role",
or "what about next?", but do not treat history as resume facts unless those
facts are also present in the retrieved context.
If the retrieved context does not answer the question, say so clearly.
Return only a concise natural-language answer.
""".strip()


class SearchRagUseCase:
    """Orchestrates session-aware RAG: rewrite query → retrieve → answer."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        vector_repository: VectorRepository,
    ):
        self._llm = llm_provider
        self._vector = vector_repository
        self._model = DEFAULT_MODEL

    @property
    def model(self) -> str:
        return self._model

    def rewrite_query(self, latest_question: str, history: str) -> str:
        """Rewrite the current question as a standalone search query."""
        rewrite_prompt = (
            "Rewrite the current question as one standalone semantic search query "
            "for a resume database. Resolve pronouns and references using the "
            "conversation history. Preserve the user's intent. Return only the "
            "rewritten query, with no explanation.\n\n"
            f"Conversation history:\n{history or '(none)'}\n\n"
            f"Current question:\n{latest_question}"
        )
        rewritten = self._llm.query(
            rewrite_prompt,
            model=DEFAULT_MODEL,
            system_prompt="You rewrite questions into standalone search queries.",
        ).strip()
        return rewritten or latest_question

    def retrieve(self, query: str) -> list[dict]:
        """Retrieve relevant chunks from the vector store."""
        return self._vector.search_semantic(query)

    def answer(self, question: str, history: str, chunks: list[dict]) -> str:
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
        return self._llm.query(
            prompt,
            model=DEFAULT_MODEL,
            system_prompt=RAG_CONVERSATION_SYSTEM_PROMPT,
        ).strip()

