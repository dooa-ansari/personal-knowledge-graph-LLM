"""ChromaDB vector repository for semantic resume search."""

from django.conf import settings

from resume_api.utils import create_embeddings, get_chroma_client


class ChromaVectorRepository:
    """ChromaDB-backed vector repository for resume chunk search."""

    def _collection(self):
        """Open the persisted collection without creating a missing index."""
        try:
            return get_chroma_client().get_collection(settings.RAG_COLLECTION_NAME)
        except Exception as exc:
            raise RuntimeError(
                "RAG index is not available. Run `python3 manage.py reindex_rag` first."
            ) from exc

    def search_semantic(
        self,
        query: str,
        top_k: int | None = None,
        where: dict | None = None,
    ) -> list[dict]:
        """Return the nearest resume chunks for a natural-language query."""
        query = query.strip()
        if not query:
            raise ValueError("Search query is required.")

        limit = top_k if top_k is not None else settings.RAG_TOP_K
        if limit < 1:
            raise ValueError("top_k must be greater than zero.")

        embedding_response = create_embeddings([query])
        query_embedding = embedding_response.data[0].embedding
        result = self._collection().query(
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