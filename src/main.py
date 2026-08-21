"""FastAPI application factory."""

from fastapi import FastAPI

from src.dependencies import SessionEnforcerMiddleware
from src.routers import convert, rag


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume RDF Converter API",
        version="1.0.0",
        description="API to convert resume markdown files to RDF and perform semantic RAG search.",
    )

    # Middleware — auto-create session cookie
    app.add_middleware(SessionEnforcerMiddleware)

    # Routers
    app.include_router(convert.router, prefix="/api")
    app.include_router(rag.router, prefix="/api")

    return app


app = create_app()