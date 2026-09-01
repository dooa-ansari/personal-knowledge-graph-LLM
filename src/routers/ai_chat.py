"""POST /api/search-rag — semantic RAG resume search."""

import logging

import requests
from openai import RateLimitError
from fastapi import APIRouter, Depends, HTTPException

from src.middlewares import get_session_id
from src.schemas.convert import ErrorResponse
from src.schemas.rag import RagSearchRequest, RagSearchResponse
from src.services.ai_chat_rag_service import search_rag

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-chat"])


@router.post(
    "/search-rag",
    response_model=RagSearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Semantic RAG resume search",
)
def search_rag_endpoint(
    body: RagSearchRequest,
    session_id: str = Depends(get_session_id),
):
    """Perform session-aware semantic retrieval and grounded answer generation."""
    try:
        logger.info("RAG search session=%s prompt=%.60s", session_id, body.prompt)
        result = search_rag(session_id, body.prompt)
        return result
    except ValueError as exc:
        logger.warning("RAG validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 429:
            logger.warning("RAG upstream rate limited by OpenRouter")
            raise HTTPException(status_code=429, detail="OpenRouter rate limit exceeded. Please retry shortly.")
        logger.exception("RAG search failed with upstream HTTP error")
        raise HTTPException(status_code=500, detail=f"Failed to perform RAG search: {exc}")
    except RateLimitError:
        logger.warning("RAG upstream rate limited by OpenRouter")
        raise HTTPException(status_code=429, detail="OpenRouter rate limit exceeded. Please retry shortly.")
    except Exception as exc:
        logger.exception("RAG search failed")
        raise HTTPException(status_code=500, detail=f"Failed to perform RAG search: {exc}")
