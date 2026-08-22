"""Thin FastAPI adapters for the local retraining control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from time import time_ns

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.concurrency import run_in_threadpool

from ml_model.retraining.dashboard_contracts import build_run_id
from web_app.application.label_review_use_case import ReviewerContext
from web_app.application.retraining_control_use_case import (
    RetrainingControlError,
    RetrainingControlUseCase,
)
from web_app.presentation.dependencies.auth import verify_internal_token
from web_app.presentation.dependencies.retraining import (
    get_retraining_control_use_case,
)
from web_app.presentation.schemas.retraining_schemas import (
    RetrainingDecisionRequest,
    RetrainingDecisionResponse,
    RetrainingDeployRequest,
    RetrainingEventResponse,
    RetrainingEvidenceSummaryResponse,
    RetrainingExportRequest,
    RetrainingExportResponse,
    RetrainingRollbackRequest,
    RetrainingRunDetailResponse,
    RetrainingRunListResponse,
    RetrainingRunRequest,
    RetrainingRunResponse,
    RetrainingRunStartResponse,
    RetrainingRetryRequest,
    RetrainingSummaryResponse,
)

router = APIRouter(
    prefix="/retraining",
    dependencies=[Depends(verify_internal_token)],
)


def _actor(request: Request) -> ReviewerContext:
    reviewer_id = request.headers.get("X-Reviewer-Id", "").strip()
    reviewer_role = request.headers.get("X-Reviewer-Role", "").strip().upper()
    if not reviewer_id or reviewer_role not in {"ANALYST", "ADMIN", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Reviewer context required")
    return ReviewerContext(reviewer_id=reviewer_id, reviewer_role=reviewer_role)


def _operator(request: Request) -> ReviewerContext:
    actor = _actor(request)
    if actor.reviewer_role not in {"ANALYST", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Operator permission required")
    return actor


def _administrator(request: Request) -> ReviewerContext:
    actor = _actor(request)
    if actor.reviewer_role != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return actor


def _raise_control_error(exc: RetrainingControlError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.safe_message) from exc


def _run_response(record) -> RetrainingRunResponse:
    payload = record.to_dict()
    # Operator notes are accepted only as bounded control metadata and are not
    # part of the browser contract; never echo them across this boundary.
    payload["operator_note"] = None
    return RetrainingRunResponse.model_validate(payload)


def _event_response(event: dict[str, object]) -> RetrainingEventResponse | None:
    raw_message = event.get("message")
    safe_message = (
        raw_message
        if isinstance(raw_message, str)
        and not any(
            marker in raw_message
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        )
        else None
    )
    payload = {
        key: event.get(key)
        for key in (
            "created_at",
            "stage",
            "outcome",
            "code",
            "duration_ms",
            "actor_id",
            "actor_role",
        )
    }
    payload["message"] = safe_message
    try:
        return RetrainingEventResponse.model_validate(payload)
    except ValueError:
        return None


@router.get("/summary", response_model=RetrainingSummaryResponse)
async def retraining_summary(
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingSummaryResponse:
    try:
        summary = await control.get_summary()
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return RetrainingSummaryResponse(
        active_model_version=summary.active_model_version,
        latest_run_state=summary.latest_run_state,
        approved_count=summary.approved_count,
        unreviewed_count=summary.unreviewed_count,
        excluded_count=summary.excluded_count,
        latest_dataset_version=summary.latest_dataset_version,
        run_in_progress=summary.run_in_progress,
        last_trigger_time=summary.last_trigger_time,
    )


@router.post(
    "/export",
    response_model=RetrainingExportResponse,
    status_code=status.HTTP_200_OK,
)
async def export_retraining_samples(
    request: Request,
    _payload: RetrainingExportRequest | None = None,
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingExportResponse:
    actor = _operator(request)
    export_id = build_run_id(
        datetime.now(timezone.utc), entropy=f"{actor.reviewer_id}:{time_ns()}"
    )
    try:
        result = await control.export_samples(export_id=export_id)
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return RetrainingExportResponse(
        export_id=export_id,
        status=result.status,
        approved_count=result.summary.approved,
        exported_count=len(result.samples),
        rejected_count=len(result.rejections),
        excluded_count=result.summary.excluded,
        quarantined=result.status == "QUARANTINED_FOR_REVIEW",
    )


@router.post(
    "/runs",
    response_model=RetrainingRunStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_retraining_run(
    request: Request,
    payload: RetrainingRunRequest,
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingRunStartResponse:
    actor = _operator(request)
    scheduled_at = None
    raw_scheduled_at = request.headers.get("X-Scheduled-At")
    if payload.trigger == "scheduled" and raw_scheduled_at:
        try:
            scheduled_at = datetime.fromisoformat(
                raw_scheduled_at.replace("Z", "+00:00")
            )
            if scheduled_at.tzinfo is None:
                raise ValueError("scheduled timestamp must include a timezone")
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Scheduled timestamp is invalid."
            ) from exc
    try:
        result = await control.start_run(
            trigger=payload.trigger,
            requested_by=actor.reviewer_id,
            requested_timezone=request.headers.get("X-Requester-Timezone", "UTC"),
            operator_note=payload.operator_note,
            scheduled_at=scheduled_at,
        )
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return RetrainingRunStartResponse(
        run_id=result.run.run_id,
        state=result.run.state,
        stage=result.run.stage,
        created=result.created,
        attempt=result.run.attempt,
    )


@router.get("/runs", response_model=RetrainingRunListResponse)
async def list_retraining_runs(
    request: Request,
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingRunListResponse:
    _actor(request)
    return RetrainingRunListResponse(
        runs=[_run_response(record) for record in control.list_runs()]
    )


@router.get(
    "/runs/{run_id}",
    response_model=RetrainingRunDetailResponse,
)
async def get_retraining_run(
    request: Request,
    run_id: str = Path(..., pattern=r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"),
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingRunDetailResponse:
    _actor(request)
    try:
        detail = control.get_run_detail(run_id)
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    events = [
        safe_event
        for event in detail.events
        if (safe_event := _event_response(event)) is not None
    ]
    return RetrainingRunDetailResponse(
        **_run_response(detail.record).model_dump(),
        events=events,
        heartbeat_age_seconds=detail.heartbeat_age_seconds,
        evidence_status=detail.evidence_status,
        retry_available=detail.retry_available,
        evidence_summary=RetrainingEvidenceSummaryResponse.model_validate(
            detail.evidence_summary.to_dict()
        ),
    )


@router.post(
    "/runs/{run_id}/retry",
    response_model=RetrainingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_retraining_run(
    request: Request,
    _payload: RetrainingRetryRequest | None = None,
    run_id: str = Path(..., pattern=r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"),
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingRunResponse:
    actor = _operator(request)
    try:
        record = await run_in_threadpool(
            control.retry_run,
            run_id=run_id,
            actor_id=actor.reviewer_id,
            actor_role=actor.reviewer_role,
        )
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return _run_response(record)


@router.post(
    "/runs/{run_id}/decision",
    response_model=RetrainingDecisionResponse,
)
async def decide_retraining_run(
    request: Request,
    payload: RetrainingDecisionRequest,
    run_id: str = Path(..., pattern=r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"),
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
) -> RetrainingDecisionResponse:
    actor = _administrator(request)
    try:
        result = control.decide(
            run_id=run_id,
            decision=payload.decision,
            reason=payload.reason,
            actor_id=actor.reviewer_id,
            actor_role=actor.reviewer_role,
        )
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return RetrainingDecisionResponse(
        decision=result.decision,
        run=_run_response(result.run),
    )


@router.post(
    "/runs/{run_id}/deploy",
    response_model=RetrainingRunResponse,
    status_code=status.HTTP_200_OK,
)
async def deploy_retraining_run(
    request: Request,
    payload: RetrainingDeployRequest,
    run_id: str = Path(..., pattern=r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"),
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
):
    actor = _administrator(request)
    try:
        result = await run_in_threadpool(
            control.deploy,
            run_id=run_id,
            expected_candidate_version=payload.expected_candidate_version,
            actor_id=actor.reviewer_id,
            actor_role=actor.reviewer_role,
        )
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return _run_response(result)


@router.post(
    "/runs/{run_id}/rollback",
    response_model=RetrainingRunResponse,
    status_code=status.HTTP_200_OK,
)
async def rollback_retraining_run(
    request: Request,
    payload: RetrainingRollbackRequest,
    run_id: str = Path(..., pattern=r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"),
    control: RetrainingControlUseCase = Depends(get_retraining_control_use_case),
):
    actor = _administrator(request)
    try:
        result = await run_in_threadpool(
            control.rollback,
            run_id=run_id,
            previous_staging_version=payload.previous_staging_version,
            reason=payload.reason,
            actor_id=actor.reviewer_id,
            actor_role=actor.reviewer_role,
        )
    except RetrainingControlError as exc:
        _raise_control_error(exc)
    return _run_response(result)


__all__ = ["get_retraining_control_use_case", "router"]
