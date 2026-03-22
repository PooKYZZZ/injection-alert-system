from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from web_app.config import get_settings
from web_app.application.triage_use_case import (
    ModelNotReadyError,
    TriageIngestCommand,
    TriageInProgressError,
    TriageUseCase,
)
from web_app.infrastructure.database import get_db
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)
from web_app.presentation.dependencies.auth import verify_internal_token
from web_app.presentation.schemas import TriageIngestRequest, TriageIngestResponse

router = APIRouter(dependencies=[Depends(verify_internal_token)])


def get_model_service(request: Request):
    return request.app.state.model_service


def get_repository(db: AsyncSession = Depends(get_db)) -> TrafficLogRepository:
    return TrafficLogRepository(db)


@router.post(
    "/triage",
    response_model=TriageIngestResponse,
    responses={
        409: {"description": "Triage ingest is already processing for this transaction_id"},
        503: {"description": "Model service is unavailable, not ready, or stale processing was detected"},
    },
)
async def ingest_triage(
    payload: TriageIngestRequest,
    model_service=Depends(get_model_service),
    repository: TrafficLogRepository = Depends(get_repository),
):
    use_case = TriageUseCase(
        classifier=model_service,
        repository=repository,
        stale_processing_timeout_seconds=get_settings().stale_processing_timeout_seconds,
    )

    try:
        result = await use_case.ingest(
            TriageIngestCommand(
                transaction_id=payload.transaction_id,
                timestamp=payload.timestamp,
                source_ip=payload.source_ip,
                request_method=payload.request_method,
                request_uri=payload.request_uri,
                request_headers=payload.request_headers,
                request_body=payload.request_body,
                http_request=payload.http_request,
                crs_score=payload.crs_score,
                crs_rule_ids=payload.crs_rule_ids,
            )
        )
    except ModelNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except TriageInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
