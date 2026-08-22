"""Dependency wiring for the local retraining control plane."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.retraining.dashboard_contracts import (
    DATASET_MANIFEST_VERSION,
    canonical_json,
    get_run_artifact_directory,
)
from ml_model.retraining.dashboard_export import EXPORTER_VERSION
from web_app.application.retraining_control_use_case import RetrainingControlUseCase
from web_app.application.retraining_export_use_case import RetrainingExportUseCase
from web_app.application.retraining_run_use_case import (
    RetrainingInputSnapshot,
    RetrainingRunUseCase,
)
from web_app.config import Settings, get_settings
from web_app.infrastructure.database import get_db
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
)
from web_app.infrastructure.repositories.traffic_label_review_repository import (
    TrafficLabelReviewRepository,
)
from web_app.infrastructure.retraining_process_runner import RetrainingProcessRunner
from web_app.infrastructure.retraining_staging_adapter import (
    LocalStagingAdapter,
    StagingDeploymentError,
    compute_artifact_digest,
)
from web_app.infrastructure.retraining_worker_supervisor import (
    RetrainingWorkerSupervisor,
)

RETRAINING_SOURCE_DATASET_VERSION = "v3_907k_cleaned"
RETRAINING_NATIVE_SOURCE_DATASET_VERSION = "v3_907k_cleaned_model_input_v2"


def _source_dataset_version_for_mode(worker_mode: str) -> str:
    if worker_mode == "smoke":
        return RETRAINING_SOURCE_DATASET_VERSION
    if worker_mode == "native":
        return RETRAINING_NATIVE_SOURCE_DATASET_VERSION
    raise ValueError("unsupported retraining worker mode")


def get_retraining_settings() -> Settings:
    return get_settings()


def _identity_digest(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _content_digest(path: Path) -> str:
    try:
        return compute_artifact_digest(path)
    except StagingDeploymentError as exc:
        raise HTTPException(
            status_code=503,
            detail="Retraining content identity is unavailable.",
        ) from exc


def _active_model_identity(request: Request) -> tuple[str, str, str]:
    model_service = getattr(request.app.state, "model_service", None)
    model_version = str(getattr(model_service, "model_version", "NOT_AVAILABLE"))
    model_input_version = str(
        getattr(model_service, "model_input_version", MODEL_INPUT_VERSION)
    )
    artifact_path = getattr(model_service, "artifact_path", None)
    if not isinstance(artifact_path, Path):
        raise HTTPException(
            status_code=503,
            detail="Retraining active model identity is unavailable.",
        )
    return (
        model_version or "NOT_AVAILABLE",
        model_input_version,
        _content_digest(artifact_path),
    )


def get_retraining_control_use_case(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_retraining_settings),
) -> RetrainingControlUseCase:
    if not settings.retraining_enabled:
        raise HTTPException(
            status_code=503,
            detail="Local retraining control is disabled.",
        )
    source_dataset_version = _source_dataset_version_for_mode(
        settings.retraining_worker_mode
    )

    review_repository = TrafficLabelReviewRepository(db)
    artifact_repository = RetrainingRunArtifactRepository(
        settings.retraining_output_root
    )
    model_version, model_input_version, active_model_digest = _active_model_identity(
        request
    )
    source_dataset_digest = _content_digest(
        Path.cwd() / "data" / "processed" / source_dataset_version
    )
    pipeline_fingerprint = _identity_digest(
        {
            "exporter_version": EXPORTER_VERSION,
            "dataset_manifest_version": DATASET_MANIFEST_VERSION,
            "preprocessing_version": model_input_version,
        }
    )

    async def snapshot_provider() -> RetrainingInputSnapshot:
        summary = await review_repository.get_retraining_review_summary()
        candidates = await review_repository.list_latest_retraining_candidates(
            limit=10_000
        )
        return RetrainingInputSnapshot(
            source_review_revisions=tuple(
                f"{candidate.traffic_log_id}:{candidate.revision}"
                for candidate in candidates
                if candidate.approval_state == "approved_for_training"
            ),
            source_dataset_version=source_dataset_version,
            source_dataset_digest=source_dataset_digest,
            pipeline_fingerprint=pipeline_fingerprint,
            active_model_version=model_version,
            active_model_digest=active_model_digest,
            approved_sample_count=summary.approved,
            review_candidates=tuple(candidates),
            review_summary=summary,
        )

    export_use_case = RetrainingExportUseCase(
        review_repository,
        output_root=artifact_repository.root,
        source_dataset_version=source_dataset_version,
        expected_preprocessing_version=model_input_version,
    )

    async def prepare_run(run_id: str, snapshot: RetrainingInputSnapshot) -> str:
        run_directory = get_run_artifact_directory(artifact_repository.root, run_id)
        export_path = run_directory / "export" / "export_manifest.json"
        samples_path = run_directory / "export" / "approved_samples.jsonl"
        if export_path.exists() or samples_path.exists():
            if not export_path.is_file() or not samples_path.is_file():
                raise ValueError("retraining export is incomplete")
            payload = json.loads(export_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("run_id") != run_id:
                raise ValueError("retraining export identity is invalid")
            status = payload.get("status")
            if status not in {"READY", "EMPTY", "QUARANTINED_FOR_REVIEW"}:
                raise ValueError("retraining export status is invalid")
            return str(status)
        result = await export_use_case.execute(
            run_id=run_id,
            candidates=snapshot.review_candidates,
            review_summary=snapshot.review_summary,
        )
        return result.status

    process_runner = RetrainingProcessRunner(
        project_root=Path.cwd(),
        smoke=settings.retraining_worker_mode == "smoke",
        timeout_seconds=settings.retraining_worker_timeout_seconds,
    )
    supervisor = RetrainingWorkerSupervisor(
        artifact_repository,
        root=artifact_repository.root,
        process_runner=process_runner,
    )
    run_use_case = RetrainingRunUseCase(
        artifact_repository,
        snapshot_provider=snapshot_provider,
        worker_supervisor=supervisor,
        run_preparer=prepare_run,
        max_retries=settings.retraining_max_retries,
    )

    def load_staging_model(path: Path, expected_version: str):
        # ModelService is imported only when an explicit local staging operation
        # needs it; ordinary API import and route tests must not load ML stacks.
        from web_app.services.model_service import ModelService

        model_settings = settings.model_copy(update={"model_registry_path": str(path)})
        service = ModelService(model_settings)
        if service.model_version != expected_version:
            raise RuntimeError("staging model version mismatch")
        result = service.predict("SELECT * FROM users WHERE id = 1")
        if not isinstance(result.get("prediction"), str) or not isinstance(
            result.get("confidence"), (int, float)
        ):
            raise RuntimeError("staging prediction smoke failed")
        return service

    def reload_staging_model(path: Path, expected_version: str):
        service = load_staging_model(path, expected_version)
        request.app.state.model_service = service
        return service

    staging_adapter = LocalStagingAdapter(
        staging_root=Path.cwd() / settings.retraining_staging_root,
        archive_root=Path.cwd() / settings.retraining_staging_archive_root,
        load_validator=load_staging_model,
        reload_callback=reload_staging_model,
    )
    return RetrainingControlUseCase(
        review_repository,
        artifact_repository,
        run_use_case,
        export_use_case,
        active_model_version=model_version,
        active_model_digest=active_model_digest,
        active_model_input_version=model_input_version,
        staging_adapter=staging_adapter,
    )


__all__ = [
    "RETRAINING_SOURCE_DATASET_VERSION",
    "get_retraining_control_use_case",
    "get_retraining_settings",
]
