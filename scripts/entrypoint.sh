#!/bin/sh
# Container entrypoint: optionally rebuild the RAG index, then start the API.
# REINDEX_ON_START=true (default) keeps the index in sync with the resume data
# on every deploy/restart; it is idempotent (drops and recreates the collection).
set -e

if [ "$REINDEX_ON_START" = "true" ]; then
  echo "Rebuilding RAG index..."
  uv run python -m scripts.reindex_embeddings \
    || echo "WARNING: reindex failed; /api/search-rag will 500 until the index exists" >&2
fi

exec uv run uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
