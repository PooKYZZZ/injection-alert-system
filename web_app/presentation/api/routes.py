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
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.application.feedback_use_case import FeedbackUseCase
from web_app.application.triage_use_case import (
    ModelNotReadyError,
    TriageInProgressError,
    TriageUseCase,
)
from web_app.application.waf_ingest_use_case import WafIngestUseCase
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
    AlertQueryParams,
    FeedbackRequest,
    MLHealthResponse,
    PredictionRequest,
    PredictionResponse,
    SourceIPSummarySchema,
    StatsResponse,
    TargetPathSummarySchema,
    TriageIngestResponse,
    TriageUpdateRequest,
    WafIngestRequest,
    WafIngestLookupResponse,
)

logger = logging.getLogger(__name__)

internal_auth_dependency = Depends(verify_internal_token)

router = APIRouter()
internal_router = APIRouter(dependencies=[internal_auth_dependency])


def get_model_service(request: Request):
    """Dependency that retrieves the singleton model service from app.state."""
    return request.app.state.model_service


def get_repository(db: AsyncSession = Depends(get_db)) -> TrafficLogRepository:
    """Dependency factory that creates a TrafficLogRepository instance."""
    from web_app.infrastructure.database import database as db_module

    session_factory = getattr(db_module, "AsyncSessionLocal", None)
    return TrafficLogRepository(db, session_factory=session_factory)


@internal_router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: Request,
    prediction_request: PredictionRequest,
    model_service=Depends(get_model_service),
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Classify an HTTP request as normal or injection attack.

    This handler is thin: it delegates to TriageUseCase which coordinates
    ML inference, confidence-gated action, and persistence.
    """
    settings = get_settings()
    use_case = TriageUseCase(
        classifier=model_service,
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


@internal_router.post(
    "/internal/waf-events",
    response_model=TriageIngestResponse,
    responses={
        409: {
            "description": "WAF ingest is already processing for this transaction_id"
        },
        503: {"description": "Model service is unavailable or not ready"},
    },
)
async def ingest_waf_event(
    payload: WafIngestRequest,
    model_service=Depends(get_model_service),
    repository: TrafficLogRepository = Depends(get_repository),
):
    settings = get_settings()
    use_case = WafIngestUseCase(
        classifier=model_service,
        repository=repository,
        stale_processing_timeout_seconds=settings.stale_processing_timeout_seconds,
        enable_preprocessing=settings.enable_http_model_preprocessing,
    )

    try:
        timestamp = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid timestamp format") from exc

    try:
        result = await use_case.execute(
            transaction_id=payload.transaction_id,
            timestamp=timestamp,
            ingest_source=payload.ingest_source,
            source_ip=payload.source_ip,
            request_method=payload.request_method,
            request_path=payload.request_path,
            query_string=payload.query_string,
            request_headers=payload.request_headers,
            sanitized_body=payload.sanitized_body or "",
            crs_score=payload.crs_score,
            crs_rule_ids=payload.crs_rule_ids,
            matched_rule_messages=payload.matched_rule_messages,
            matched_rule_tags=payload.matched_rule_tags,
        )
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TriageInProgressError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc

    return TriageIngestResponse(
        alert_id=result.alert_id,
        prediction=result.prediction,
        confidence=result.confidence,
        confidence_level=result.confidence_level,
        action_taken=result.action_taken,
        model_version=result.model_version,
    )


@internal_router.get(
    "/internal/waf-events/{transaction_id}",
    response_model=WafIngestLookupResponse,
)
async def get_waf_ingest_by_transaction_id(
    transaction_id: str,
    repository: TrafficLogRepository = Depends(get_repository),
):
    entity = await repository.get_by_transaction_id(transaction_id)
    if entity is None:
        return WafIngestLookupResponse(
            found=False,
            transaction_id=transaction_id,
        )

    return WafIngestLookupResponse(
        found=True,
        transaction_id=transaction_id,
        alert_id=entity.id,
        status=entity.status,
        prediction=entity.prediction,
        confidence=entity.confidence,
        confidence_level=entity.confidence_level,
        action_taken=entity.action_taken,
        ingest_source=entity.ingest_source,
        crs_score=entity.crs_score,
        crs_rule_ids=entity.crs_rule_ids,
        matched_rule_messages=entity.matched_rule_messages,
        matched_rule_tags=entity.matched_rule_tags,
        timestamp=entity.timestamp,
    )


@internal_router.get("/stats", response_model=StatsResponse)
async def get_stats(
    response: Response,
    request: Request,
    window: Literal["1h", "6h", "24h", "7d"] | None = Query(
        default=None, description="Time window for stats (all-time if not specified)"
    ),
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Return aggregate traffic statistics with zero-safe defaults.

    Optional window parameter filters stats to the specified time period.
    No window = all-time stats.
    """
    reference_time = datetime.now(timezone.utc)
    timezone_name = (
        request.query_params.get("timezone_name")
        or request.query_params.get("timezone")
        or None
    )
    summary = await repository.get_stats_summary(
        window=window,
        reference_time=reference_time,
    )
    # Get real activity buckets from database for hero activity strip (graceful degradation)
    activity_buckets_list = []
    try:
        activity_buckets = await repository.get_activity_buckets(
            window=window,
            reference_time=reference_time,
            timezone_name=timezone_name,
        )
        activity_buckets_list = [
            ActivityBucketSchema(
                bucket_index=b.bucket_index,
                total_count=b.total_count,
                blocked_count=b.blocked_count,
                allowed_count=b.allowed_count,
                throttled_count=b.throttled_count,
                timestamp_start=b.timestamp_start,
                timestamp_end=b.timestamp_end,
                bucket_width_seconds=b.bucket_width_seconds,
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

    response.headers["Cache-Control"] = "private, max-age=5"

    return StatsResponse(
        total_requests=summary.total_requests,
        counts_by_label=summary.counts_by_label,
        avg_inference_latency_ms=summary.avg_inference_latency_ms,
        blocked_count=summary.blocked_count,
        allowed_count=summary.allowed_count,
        throttled_count=summary.throttled_count,
        avg_confidence=summary.avg_confidence,
        false_positive_rate=summary.false_positive_rate,
        false_positive_count=summary.false_positive_count,
        high_alert_count=summary.high_alert_count,
        prev_high_alert_count=summary.prev_high_alert_count,
        prev_total_requests=summary.prev_total_requests,
        prev_blocked_count=summary.prev_blocked_count,
        prev_allowed_count=summary.prev_allowed_count,
        prev_throttled_count=summary.prev_throttled_count,
        activity_buckets=activity_buckets_list,
        attack_distribution=summary.attack_distribution,
        top_source_ips=top_source_ips_list,
        top_targeted_paths=top_targeted_paths_list,
    )


@internal_router.get("/ml-health", response_model=MLHealthResponse)
async def get_ml_health(
    response: Response,
    model_service=Depends(get_model_service),
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Return health information for the currently loaded model service."""
    # Get real drift metrics from database (graceful degradation for DB unavailability)
    drift_detected = False
    drift_score: float | None = None

    try:
        drift_metrics = await repository.get_drift_metrics(recent_window=100)
        drift_detected = drift_metrics.drift_detected
        drift_score = drift_metrics.drift_score
    except SQLAlchemyError as e:
        # Database not available - drift detection unavailable
        logger.warning("Database unavailable while computing drift metrics: %s", e)

    # Get eval metadata from model service (returns empty dict if not available)
    eval_metadata = model_service.eval_metadata

    response.headers["Cache-Control"] = "private, max-age=5"

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
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Return a single alert by primary key or 404 when it does not exist."""
    entity = await repository.get_by_id(alert_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertDetailResponse.model_validate(entity)


@internal_router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    query: AlertQueryParams = Depends(),
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Get list of traffic alerts with full filtering support."""
    alert_page = await repository.get_alert_list(
        page=query.page,
        page_size=query.page_size,
        severity=query.severity,
        time_range=query.time_range,
        search=query.search,
        action=query.action,
        triage_status=query.triage_status,
        confidence_levels=query.confidence_level,
        prediction=query.prediction,
        source_ip=query.source_ip,
        sort_by=query.sort_by,
        sort_dir=query.sort_dir,
    )
    return AlertListResponse(
        items=[
            AlertDetailResponse.model_validate(entity) for entity in alert_page.items
        ],
        total=alert_page.total,
        page=alert_page.page,
        page_size=alert_page.page_size,
    )


@internal_router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Store analyst feedback/correction for a prediction."""
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
    repository: TrafficLogRepository = Depends(get_repository),
):
    """Update the triage status of an alert."""
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
