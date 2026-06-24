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

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web_app.application.inference_queue import InferenceQueueService
from web_app.config import get_settings
from web_app.infrastructure.database import init_db
from web_app.presentation.api.routes import router as api_router
from web_app.presentation.api.triage_router import router as triage_router
from web_app.presentation.health import health_check
from web_app.presentation.middleware.body_limit import BodySizeLimitMiddleware
from web_app.presentation.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from web_app.presentation.schemas import HealthResponse
from web_app.services.model_service import ModelService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    settings = get_settings()

    if settings.is_development or settings.is_testing:
        await init_db()

    # ── Startup: Load model with fallback to mock mode ─────────────────────────
    # In production mode, fail fast on model load errors (convert to RuntimeError).
    # In development/testing, allow fallback to mock mode.
    try:
        model_service = ModelService(settings)
        logger.info("Model loaded successfully from %s", settings.model_registry_path)
    except RuntimeError:
        # Re-raise RuntimeError to fail fast in production mode
        raise
    except FileNotFoundError as exc:
        # In production, convert FileNotFoundError to RuntimeError for consistent error contract
        # In testing/development, fall back to mock mode
        if settings.is_production:
            raise RuntimeError(str(exc)) from exc
        logger.warning(
            "Model load failed — %s. "
            "Starting in mock mode. Predictions will be simulated. "
            "To use the real model, set MODEL_REGISTRY_PATH correctly in .env "
            "and ensure model files are present at that path.",
            exc,
        )
        model_service = ModelService.create_mock()
    except Exception as exc:
        if settings.is_production:
            # In production, fail fast on any model load error
            raise
        logger.warning(
            "Model load failed — %s. "
            "Starting in mock mode. Predictions will be simulated. "
            "To use the real model, set MODEL_REGISTRY_PATH correctly in .env "
            "and ensure model files are present at that path.",
            exc,
        )
        model_service = ModelService.create_mock()

    app.state.model_service = model_service
    app.state.inference_queue = InferenceQueueService(settings)
    try:
        await app.state.inference_queue.start()
    except Exception as exc:
        logger.warning(
            "Inference queue failed to start: %s",
            exc.__class__.__name__,
        )

    try:
        yield
    finally:
        # ── Shutdown ──────────────────────────────────────────────────────────────
        queue = getattr(app.state, "inference_queue", None)
        if queue is not None:
            await queue.stop()


def create_app() -> FastAPI:
    """Application factory — the single place where FastAPI is configured."""
    settings = get_settings()

    # Configure docs endpoint based on environment
    docs_url = "/docs" if settings.enable_api_docs else None
    redoc_url = "/redoc" if settings.enable_api_docs else None

    app = FastAPI(
        title="Injection Alert Classification System",
        description="API for classifying HTTP requests as normal or injection attacks",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url="/openapi.json" if settings.enable_api_docs else None,
    )

    # --- CORS middleware ---
    # In production/staging, use more restrictive CORS settings
    if settings.is_production or settings.is_staging:
        # Production: be more restrictive - only allow explicitly configured origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Authorization", "Content-Type"],
        )
    else:
        # Development: allow more flexibility for local development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Starlette applies middleware in reverse registration order.
    # Register the body limit middleware first so the security headers
    # middleware becomes the outermost custom layer and can post-process
    # every response, including early 400/413 responses from body limits.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # --- API router ---
    app.include_router(api_router, prefix="/api")
    app.include_router(triage_router, prefix="/api")

    # --- Canonical health endpoint (single source of truth) ---
    app.add_api_route("/health", health_check, response_model=HealthResponse)
    app.add_api_route("/api/health", health_check, response_model=HealthResponse)

    return app
