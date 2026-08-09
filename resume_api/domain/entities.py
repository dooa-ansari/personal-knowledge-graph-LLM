"""Domain entities representing resume concepts."""

from dataclasses import dataclass, field


@dataclass
class RagChunk:
    id: str
    document: str
    metadata: dict


@dataclass
class RagResult:
    prompt: str
    session_id: str
    model: str
    retrieval_query: str
    answer: str
    retrieved_chunks: list[RagChunk]