"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.middlewares import SessionEnforcerMiddleware
from src.routers import parse_resume, ai_chat


def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowledge Graph API",
        version="1.0.0",
        description="API to convert resume markdown files to RDF and perform semantic RAG search.",
    )

    # CORS Middleware — allow frontend development server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware — auto-create session cookie
    app.add_middleware(SessionEnforcerMiddleware)

    # Routers
    app.include_router(parse_resume.router, prefix="/api")
    app.include_router(ai_chat.router, prefix="/api")

    return app


app = create_app()
