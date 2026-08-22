"""Request/response schemas for the RAG search endpoint."""

from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Question to ask about the resume")


class RagChunk(BaseModel):
    document: str
    metadata: dict[str, str] = {}
    distance: float | None = None
    score: float | None = None


class RagSearchResponse(BaseModel):
    prompt: str
    session_id: str
    model: str
    retrieval_query: str
    answer: str
    retrieved_chunks: list[RagChunk]