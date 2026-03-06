"""
web_app/presentation/app.py

Single canonical FastAPI application factory.

Architectural role:
  - Presentation layer entry point
  - Initializes the app, lifespan, CORS, and middleware
  - Creates singleton model loader and stores it on app.state
  - Includes all API routers

Dependency rule:
  - May import from application/ (use cases) and infrastructure/ (DI bindings)
  - Never imports domain entities directly; communicates through application services
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.config import get_settings
from web_app.infrastructure.database import get_db, init_db, TrafficLog
from web_app.presentation.schemas import HealthResponse
from web_app.presentation.api.routes import router as api_router
from ml_model.models.mock_model import MockInjectionClassifier


settings = get_settings()


def _create_model() -> MockInjectionClassifier:
    """Create and return the singleton injection classifier.

    This will be replaced with a real model loader that reads from
    model_registry/production/ once the trained model is available.
    """
    return MockInjectionClassifier()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup — initialize DB tables and singleton model
    await init_db()
    app.state.model = _create_model()
    yield
    # Shutdown (cleanup if needed)


def create_app() -> FastAPI:
    """Application factory — the single place where FastAPI is configured."""
    app = FastAPI(
        title="Injection Alert Classification System",
        description="API for classifying HTTP requests as normal or injection attacks",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- CORS middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- API router ---
    app.include_router(api_router, prefix="/api")

    # --- Canonical health endpoint (single source of truth) ---
    @app.get("/health", response_model=HealthResponse)
    async def health_check(db: AsyncSession = Depends(get_db)):
        """Health check endpoint with database connectivity probe."""
        try:
            result = await db.execute(select(TrafficLog.id).limit(1))
            result.first()
            return HealthResponse(status="healthy", database="connected")
        except Exception:
            return HealthResponse(status="unhealthy", database="disconnected")

    return app


# Module-level app instance used by uvicorn and TestClient
app = create_app()
