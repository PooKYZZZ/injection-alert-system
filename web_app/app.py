from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from web_app.config import get_settings
from web_app.database import get_db, init_db, TrafficLog
from web_app.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse,
    HealthResponse
)
from web_app.api.routes import router as api_router
from ml_model.models.mock_model import MockInjectionClassifier

settings = get_settings()
model = MockInjectionClassifier()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="Injection Alert Classification System",
    description="API for classifying HTTP requests as normal or injection attacks",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database connection
        db.query(TrafficLog.id).first()
        return HealthResponse(status="healthy", database="connected")
    except Exception:
        return HealthResponse(status="unhealthy", database="disconnected")
