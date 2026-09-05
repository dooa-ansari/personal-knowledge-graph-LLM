FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir uv
RUN uv sync --no-dev

EXPOSE 8000

# Railway injects PORT at runtime; the default keeps local/compose usage on 8000.
ENV PORT=8000
# Rebuild the RAG index on container start (requires OPENROUTER_API_KEY).
ENV REINDEX_ON_START=true

ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
