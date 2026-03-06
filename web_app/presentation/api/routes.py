"""
web_app/presentation/api/routes.py

Thin HTTP route handlers for the Injection Alert System API.

Architectural role:
  - Presentation layer — converts HTTP requests into application-layer calls
  - Route handlers are thin: validate input, call use case, return response
  - No ORM model creation or DB commits in handlers

Dependency rule:
  - Calls application/ use cases for all business logic
  - Uses presentation/schemas/ for request/response serialization
  - Gets DB session from infrastructure/ DI only to construct repositories
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from web_app.infrastructure.database import get_db
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)
from web_app.application.triage_use_case import TriageUseCase
from web_app.application.feedback_use_case import FeedbackUseCase
from web_app.presentation.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse,
)

router = APIRouter()


def get_model(request: Request):
    """Dependency that retrieves the singleton model from app.state."""
    return request.app.state.model


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: Request,
    prediction_request: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    model=Depends(get_model),
):
    """Classify an HTTP request as normal or injection attack.

    This handler is thin: it delegates to TriageUseCase which coordinates
    ML inference, confidence-gated action, and persistence.
    """
    repository = TrafficLogRepository(db)
    use_case = TriageUseCase(classifier=model, repository=repository)

    result = await use_case.execute(
        http_request=prediction_request.http_request,
        source_ip=request.client.host if request.client else "unknown",
    )

    return PredictionResponse(
        class_label=result.class_label,
        confidence=result.confidence,
        confidence_level=result.confidence_level,
        action_taken=result.action_taken,
    )


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get list of traffic alerts with pagination."""
    repository = TrafficLogRepository(db)
    entities = await repository.list_recent(skip=skip, limit=limit)
    return [
        AlertResponse(
            id=e.id,
            timestamp=e.timestamp,
            source_ip=e.source_ip,
            http_request=e.http_request,
            prediction=e.prediction,
            confidence=e.confidence,
            confidence_level=e.confidence_level,
            action_taken=e.action_taken,
            analyst_label=e.analyst_label,
            labeled_at=e.labeled_at,
            labeled_by=e.labeled_by,
        )
        for e in entities
    ]


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Store analyst feedback/correction for a prediction."""
    repository = TrafficLogRepository(db)
    use_case = FeedbackUseCase(repository=repository)

    result = await use_case.execute(
        traffic_id=feedback.traffic_id,
        correct_label=feedback.correct_label,
        analyst_email=feedback.analyst_email,
    )

    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return {"message": result.message, "traffic_id": result.traffic_id}
