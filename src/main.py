"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from src import config
from src.middlewares import SessionEnforcerMiddleware
from src.rate_limiter import limiter
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

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Routers
    app.include_router(parse_resume.router, prefix="/api")
    app.include_router(ai_chat.router, prefix="/api")

    return app


app = create_app()
