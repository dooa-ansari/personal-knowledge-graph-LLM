"""Repository port interfaces for dependency inversion."""

from abc import ABC, abstractmethod
from typing import Optional

from resume_api.domain.entities import RagChunk


class VectorRepository(ABC):
    """Port interface for vector database operations."""

    @abstractmethod
    def search_semantic(
        self,
        query: str,
        top_k: int | None = None,
        where: dict | None = None,
    ) -> list[dict]:
        """Search for semantically similar chunks."""
        ...


class LLMProvider(ABC):
    """Port interface for language model operations."""

    @abstractmethod
    def query(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a prompt to the LLM and return the response."""
        ...


class RDFRepository(ABC):
    """Port interface for RDF conversion operations."""

    @abstractmethod
    def convert_resume_to_rdf(self, md_path: str) -> str:
        """Convert a resume markdown file to RDF Turtle format."""
        ...


class EmbeddingProvider(ABC):
    """Port interface for embedding operations."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a single query string."""
        ...