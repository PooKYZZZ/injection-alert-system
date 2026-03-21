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

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.application.feedback_use_case import FeedbackUseCase
from web_app.application.triage_use_case import TriageUseCase
from web_app.config import get_settings
from web_app.infrastructure.database import get_db
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)
from web_app.presentation.dependencies.auth import verify_internal_token
from web_app.application.update_alert_triage_use_case import (
    UpdateAlertTriageUseCase,
    InvalidTriageStatusError,
)
from web_app.presentation.schemas import (
    ActivityBucketSchema,
    AlertDetailResponse,
    AlertListResponse,
    FeedbackRequest,
    MLHealthResponse,
    PredictionRequest,
    PredictionResponse,
    SourceIPSummarySchema,
    StatsResponse,
    TargetPathSummarySchema,
    TriageUpdateRequest,
)

logger = logging.getLogger(__name__)

internal_auth_dependency = Depends(verify_internal_token)

router = APIRouter()
internal_router = APIRouter(dependencies=[internal_auth_dependency])


def get_model(request: Request):
    """Dependency that retrieves the singleton model from app.state."""
    return request.app.state.model


def get_model_service(request: Request):
    """Dependency that retrieves the singleton model service from app.state."""
    return request.app.state.model_service


@internal_router.post("/predict", response_model=PredictionResponse)
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
    settings = get_settings()
    repository = TrafficLogRepository(db)
    use_case = TriageUseCase(
        classifier=model,
        repository=repository,
        enable_preprocessing=settings.enable_http_model_preprocessing,
    )

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


@internal_router.get("/stats", response_model=StatsResponse)
async def get_stats(
    window: Literal["1h", "6h", "24h", "7d"] | None = Query(
        default=None, description="Time window for stats (all-time if not specified)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate traffic statistics with zero-safe defaults.

    Optional window parameter filters stats to the specified time period.
    No window = all-time stats.
    """
    repository = TrafficLogRepository(db)
    summary = await repository.get_stats_summary(window=window)
    # Get real activity buckets from database for hero activity strip (graceful degradation)
    activity_buckets_list = []
    try:
        activity_buckets = await repository.get_activity_buckets(window=window)
        activity_buckets_list = [
            ActivityBucketSchema(
                bucket_index=b.bucket_index,
                total_count=b.total_count,
                blocked_count=b.blocked_count,
                allowed_count=b.allowed_count,
                throttled_count=b.throttled_count,
                timestamp_start=b.timestamp_start,
            )
            for b in activity_buckets
        ]
    except SQLAlchemyError as e:
        # Database not available or not initialized - return empty buckets
        logger.warning("Database unavailable while fetching activity buckets: %s", e)

    # Build top source IPs list
    top_source_ips_list = [
        SourceIPSummarySchema(
            ip=ip.ip,
            count=ip.count,
            action=ip.action,
        )
        for ip in summary.top_source_ips
    ]

    # Build top targeted paths list
    top_targeted_paths_list = [
        TargetPathSummarySchema(
            path=path.path,
            hits=path.hits,
        )
        for path in summary.top_targeted_paths
    ]

    return StatsResponse(
        total_requests=summary.total_requests,
        counts_by_label=summary.counts_by_label,
        avg_inference_latency_ms=summary.avg_inference_latency_ms,
        blocked_count=summary.blocked_count,
        allowed_count=summary.allowed_count,
        throttled_count=summary.throttled_count,
        avg_confidence=summary.avg_confidence,
        activity_buckets=activity_buckets_list,
        attack_distribution=summary.attack_distribution,
        top_source_ips=top_source_ips_list,
        top_targeted_paths=top_targeted_paths_list,
    )


@internal_router.get("/ml-health", response_model=MLHealthResponse)
async def get_ml_health(
    model_service=Depends(get_model_service),
    db: AsyncSession = Depends(get_db),
):
    """Return health information for the currently loaded model service."""
    # Get real drift metrics from database (graceful degradation for DB unavailability)
    drift_detected = False
    drift_score: float | None = None

    try:
        repository = TrafficLogRepository(db)
        drift_metrics = await repository.get_drift_metrics(recent_window=100)
        drift_detected = drift_metrics.drift_detected
        drift_score = drift_metrics.drift_score
    except SQLAlchemyError as e:
        # Database not available - drift detection unavailable
        logger.warning("Database unavailable while computing drift metrics: %s", e)

    # Get eval metadata from model service (returns empty dict if not available)
    eval_metadata = model_service.eval_metadata

    return MLHealthResponse(
        model_version=model_service.model_version,
        loaded=model_service.loaded,
        status="degraded" if model_service.is_mock else "healthy",
        avg_inference_latency_ms=model_service.avg_inference_latency_ms,
        total_processed=model_service.total_processed,
        drift_detected=drift_detected,
        drift_score=drift_score,
        confidence_thresholds=model_service.confidence_thresholds,
        # Optional eval metadata from model registry artifacts
        macro_f1=eval_metadata.get("macro_f1"),
        ece=eval_metadata.get("ece"),
        per_class_f1=eval_metadata.get("per_class_f1") or {},
        calibration_bins=eval_metadata.get("calibration_bins") or [],
        prediction_distribution=eval_metadata.get("prediction_distribution") or {},
    )


@internal_router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
async def get_alert_by_id(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a single alert by primary key or 404 when it does not exist."""
    repository = TrafficLogRepository(db)
    entity = await repository.get_by_id(alert_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertDetailResponse.model_validate(entity)


@internal_router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    severity: Literal["ALL", "LOW", "MEDIUM", "HIGH"] | None = Query(default=None),
    time_range: Literal["1h", "6h", "24h", "7d"] | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get list of traffic alerts with pagination."""
    repository = TrafficLogRepository(db)
    alert_page = await repository.get_alert_list(
        page=page,
        page_size=page_size,
        severity=severity,
        time_range=time_range,
        search=search,
    )
    return AlertListResponse(
        items=[
            AlertDetailResponse.model_validate(entity) for entity in alert_page.items
        ],
        total=alert_page.total,
        page=alert_page.page,
        page_size=alert_page.page_size,
    )


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


@internal_router.patch("/alerts/{alert_id}/triage", response_model=AlertDetailResponse)
async def update_alert_triage(
    alert_id: int,
    request: TriageUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update the triage status of an alert."""
    repository = TrafficLogRepository(db)
    use_case = UpdateAlertTriageUseCase(repository=repository)

    try:
        result = await use_case.execute(
            alert_id=alert_id,
            triage_status=request.triage_status,
        )
    except InvalidTriageStatusError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return AlertDetailResponse.model_validate(result.alert)


router.include_router(internal_router)
