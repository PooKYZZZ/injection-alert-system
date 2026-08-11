"""Strict, redaction-safe schemas for the retraining control plane."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ml_model.retraining.dashboard_contracts import RunState

RUN_ID_PATTERN = r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$"
MODEL_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrainingRunRequest(StrictSchema):
    trigger: Literal["manual", "scheduled"]
    operator_note: str | None = Field(default=None, max_length=500)

    @field_validator("operator_note")
    @classmethod
    def reject_raw_payload_markers(cls, value: str | None) -> str | None:
        if value is not None and any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise ValueError("operator note contains control characters")
        if value is not None and any(
            marker in value
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise ValueError("operator note contains forbidden content")
        return value


class RetrainingExportRequest(StrictSchema):
    """The export endpoint intentionally has no client-selectable options."""

    pass


class RetrainingDecisionRequest(StrictSchema):
    decision: Literal["approve", "hold", "reject"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def reject_raw_payload_markers(cls, value: str | None) -> str | None:
        if value is not None and any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise ValueError("decision reason contains control characters")
        if value is not None and any(
            marker in value
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise ValueError("decision reason contains forbidden content")
        return value


class RetrainingDeployRequest(StrictSchema):
    expected_candidate_version: str = Field(
        ..., pattern=MODEL_VERSION_PATTERN, max_length=128
    )


class RetrainingRollbackRequest(StrictSchema):
    previous_staging_version: str = Field(
        ..., pattern=MODEL_VERSION_PATTERN, max_length=128
    )
    reason: str = Field(..., min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reject_raw_payload_markers(cls, value: str) -> str:
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("rollback reason contains control characters")
        if any(
            marker in value
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise ValueError("rollback reason contains forbidden content")
        return value


class RetrainingRunResponse(StrictSchema):
    run_id: str = Field(..., pattern=RUN_ID_PATTERN)
    state: RunState
    stage: str = Field(..., max_length=64)
    attempt: int = Field(..., ge=0)
    retry_count: int = Field(..., ge=0)
    max_retries: int = Field(..., ge=0)
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime | None = None
    trigger: Literal["manual", "scheduled"]
    requested_by: str = Field(..., min_length=1, max_length=128)
    requested_timezone: str = Field(..., min_length=1, max_length=64)
    input_fingerprint: str = Field(..., min_length=64, max_length=64)
    source_review_revisions: list[str]
    source_dataset_version: str
    source_dataset_digest: str = Field(..., min_length=64, max_length=64)
    pipeline_fingerprint: str = Field(..., min_length=64, max_length=64)
    active_model_version: str
    active_model_digest: str = Field(..., min_length=64, max_length=64)
    approved_sample_count: int = Field(..., ge=0)
    operator_note: str | None = Field(default=None, max_length=500)
    worker_id: str | None = Field(default=None, max_length=128)
    next_retry_at: datetime | None = None
    dataset_version: str | None = None
    dataset_digest: str | None = Field(default=None, min_length=64, max_length=64)
    candidate_model_version: str | None = None
    candidate_model_digest: str | None = Field(
        default=None, min_length=64, max_length=64
    )
    evaluation_digest: str | None = Field(default=None, min_length=64, max_length=64)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=500)
    generation: int = Field(..., ge=1)


class RetrainingRunStartResponse(StrictSchema):
    run_id: str = Field(..., pattern=RUN_ID_PATTERN)
    state: RunState
    stage: str = Field(..., max_length=64)
    created: bool
    attempt: int = Field(..., ge=0)


class RetrainingRunListResponse(StrictSchema):
    runs: list[RetrainingRunResponse]


class RetrainingEventResponse(StrictSchema):
    created_at: datetime
    stage: str = Field(..., max_length=64)
    outcome: str = Field(..., max_length=32)
    code: str = Field(..., max_length=64)
    message: str | None = Field(default=None, max_length=500)
    duration_ms: int | None = Field(default=None, ge=0)
    actor_id: str | None = Field(default=None, max_length=128)
    actor_role: str | None = Field(default=None, max_length=32)


class RetrainingRunDetailResponse(RetrainingRunResponse):
    events: list[RetrainingEventResponse]
    heartbeat_age_seconds: int | None = Field(default=None, ge=0)
    evidence_status: Literal[
        "VERIFIED", "NATIVE", "CONTROLLED_SMOKE", "NOT_RUN", "NOT_ENOUGH_EVIDENCE"
    ]
    retry_available: bool


class RetrainingSummaryResponse(StrictSchema):
    active_model_version: str
    latest_run_state: RunState | None = None
    approved_count: int = Field(..., ge=0)
    unreviewed_count: int = Field(..., ge=0)
    excluded_count: int = Field(..., ge=0)
    latest_dataset_version: str | None = None
    run_in_progress: bool
    last_trigger_time: datetime | None = None


class RetrainingExportResponse(StrictSchema):
    export_id: str = Field(..., pattern=RUN_ID_PATTERN)
    status: Literal["READY", "EMPTY", "QUARANTINED_FOR_REVIEW"]
    approved_count: int = Field(..., ge=0)
    exported_count: int = Field(..., ge=0)
    rejected_count: int = Field(..., ge=0)
    excluded_count: int = Field(..., ge=0)
    quarantined: bool


class RetrainingDecisionResponse(StrictSchema):
    decision: Literal["approve", "hold", "reject"]
    run: RetrainingRunResponse


class RetrainingOperationResponse(StrictSchema):
    status: Literal["NOT_AVAILABLE"]
    code: str


__all__ = [
    "RetrainingDecisionRequest",
    "RetrainingDecisionResponse",
    "RetrainingDeployRequest",
    "RetrainingEventResponse",
    "RetrainingExportRequest",
    "RetrainingExportResponse",
    "RetrainingOperationResponse",
    "RetrainingRollbackRequest",
    "RetrainingRunDetailResponse",
    "RetrainingRunListResponse",
    "RetrainingRunRequest",
    "RetrainingRunResponse",
    "RetrainingRunStartResponse",
    "RetrainingSummaryResponse",
]
