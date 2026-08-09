"""Concrete vector repository adapter wrapping the existing ChromaDB service."""

from resume_api.ports.repositories import VectorRepository
from resume_api.services.vector_search_service import search_semantic


class ChromaVectorRepository(VectorRepository):
    """Adapter that wraps the existing ChromaDB search service as a VectorRepository."""

    def search_semantic(
        self,
        query: str,
        top_k: int | None = None,
        where: dict | None = None,
    ) -> list[dict]:
        return search_semantic(query=query, top_k=top_k, where=where)