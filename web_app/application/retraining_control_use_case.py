"""Application services for the retraining control-plane boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from ml_model.retraining.dashboard_contracts import EvidenceStatus, RunState
from ml_model.retraining.dashboard_export import DashboardExportResult
from web_app.application.retraining_export_use_case import RetrainingExportUseCase
from web_app.application.retraining_run_use_case import (
    RetrainingRunUseCase,
    RetrainingStartResult,
)
from web_app.domain.interfaces import ITrafficLabelReviewRepository
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactRepositoryError,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)
from web_app.infrastructure.retraining_staging_adapter import (
    LocalStagingAdapter,
    StagingDeploymentError,
    StagingDeploymentRecord,
)

RUNNING_STATES = frozenset(
    {
        RunState.QUEUED,
        RunState.EXPORTING,
        RunState.DATASET_VALIDATED,
        RunState.TRAINING,
        RunState.EVALUATING,
        RunState.DEPLOYING,
        RunState.RECOVERY_REQUIRED,
    }
)


class RetrainingControlError(ValueError):
    """Bounded application error mapped to a safe HTTP response."""

    def __init__(self, code: str, message: str, *, status_code: int = 409) -> None:
        self.code = code
        self.safe_message = message[:240].replace("\r", " ").replace("\n", " ")
        self.status_code = status_code
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class RetrainingSummarySnapshot:
    active_model_version: str
    latest_run_state: RunState | None
    approved_count: int
    unreviewed_count: int
    excluded_count: int
    latest_dataset_version: str | None
    run_in_progress: bool
    last_trigger_time: datetime | None


@dataclass(frozen=True, slots=True)
class RetrainingRunDetail:
    record: RetrainingRunRecord
    events: tuple[dict[str, Any], ...]
    evidence_status: str
    heartbeat_age_seconds: int | None
    retry_available: bool


@dataclass(frozen=True, slots=True)
class RetrainingDecisionResult:
    run: RetrainingRunRecord
    decision: str


class RetrainingControlUseCase:
    """Coordinate safe API operations without putting policy in route handlers."""

    def __init__(
        self,
        review_repository: ITrafficLabelReviewRepository,
        artifact_repository: RetrainingRunArtifactRepository,
        run_use_case: RetrainingRunUseCase,
        export_use_case: RetrainingExportUseCase,
        *,
        active_model_version: str = "NOT_AVAILABLE",
        active_model_digest: str | None = None,
        active_model_input_version: str | None = None,
        staging_adapter: LocalStagingAdapter | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._review_repository = review_repository
        self._artifact_repository = artifact_repository
        self._run_use_case = run_use_case
        self._export_use_case = export_use_case
        self._active_model_version = active_model_version
        self._active_model_digest = active_model_digest
        self._active_model_input_version = active_model_input_version
        self._staging_adapter = staging_adapter
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def get_summary(self) -> RetrainingSummarySnapshot:
        review_summary = await self._review_repository.get_retraining_review_summary()
        runs = self._artifact_repository.list_runs()
        latest = runs[-1] if runs else None
        latest_dataset_version = next(
            (
                record.dataset_version
                for record in reversed(runs)
                if record.dataset_version
            ),
            None,
        )
        return RetrainingSummarySnapshot(
            active_model_version=self._active_model_version,
            latest_run_state=latest.state if latest else None,
            approved_count=review_summary.approved,
            unreviewed_count=review_summary.unreviewed,
            excluded_count=review_summary.excluded,
            latest_dataset_version=latest_dataset_version,
            run_in_progress=any(record.state in RUNNING_STATES for record in runs),
            last_trigger_time=latest.created_at if latest else None,
        )

    async def start_run(self, **kwargs: Any) -> RetrainingStartResult:
        return await self._run_use_case.start_run(**kwargs)

    async def export_samples(self, *, export_id: str) -> DashboardExportResult:
        return await self._export_use_case.execute(run_id=export_id)

    def list_runs(self) -> list[RetrainingRunRecord]:
        return list(reversed(self._artifact_repository.list_runs()))

    def get_run_detail(self, run_id: str) -> RetrainingRunDetail:
        try:
            record = self._artifact_repository.load_run(run_id)
            events = tuple(self._artifact_repository.read_events(run_id))
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "RUN_NOT_FOUND", "The retraining run was not found.", status_code=404
            ) from exc
        now = self._clock().astimezone(timezone.utc)
        heartbeat_age = None
        if record.heartbeat_at is not None:
            heartbeat_age = max(0, int((now - record.heartbeat_at).total_seconds()))
        evidence_status = (
            "NOT_ENOUGH_EVIDENCE"
            if record.state is RunState.NOT_ENOUGH_EVIDENCE
            else "NOT_RUN"
        )
        try:
            evaluation = self._artifact_repository.read_json_artifact(
                record.run_id, "stages/evaluation.json"
            )
            evidence_status = EvidenceStatus.parse(
                evaluation.get("evidence_status")
            ).value
        except (
            ArtifactRepositoryError,
            FileNotFoundError,
            TypeError,
            ValueError,
        ):
            pass
        return RetrainingRunDetail(
            record=record,
            events=events,
            evidence_status=evidence_status,
            heartbeat_age_seconds=heartbeat_age,
            retry_available=(
                record.state is RunState.RETRYABLE_FAILED
                and record.retry_count < record.max_retries
            ),
        )

    def decide(
        self,
        *,
        run_id: str,
        decision: str,
        reason: str | None,
        actor_id: str,
        actor_role: str,
    ) -> RetrainingDecisionResult:
        if actor_role != "ADMIN":
            raise RetrainingControlError(
                "FORBIDDEN", "Administrator review is required.", status_code=403
            )
        if decision not in {"approve", "hold", "reject"}:
            raise RetrainingControlError("INVALID_DECISION", "Decision is invalid.")
        if not actor_id.strip() or len(actor_id) > 128:
            raise RetrainingControlError(
                "INVALID_ACTOR", "Reviewer identity is invalid."
            )
        if reason is not None and len(reason) > 500:
            raise RetrainingControlError(
                "INVALID_REASON", "Decision reason is too long."
            )
        if reason is not None and any(
            marker in reason
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise RetrainingControlError(
                "INVALID_REASON", "Decision reason contains forbidden content."
            )
        if decision in {"hold", "reject"} and not (reason or "").strip():
            raise RetrainingControlError(
                "REASON_REQUIRED", "A reason is required for hold or reject."
            )

        try:
            current = self._artifact_repository.load_run(run_id)
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "RUN_NOT_FOUND", "The retraining run was not found.", status_code=404
            ) from exc
        if current.state is not RunState.PENDING_APPROVAL:
            raise RetrainingControlError(
                "RUN_NOT_PENDING", "The run is not awaiting a reviewer decision."
            )
        if decision == "approve" and not (
            current.candidate_model_version
            and current.candidate_model_digest
            and current.evaluation_digest
        ):
            raise RetrainingControlError(
                "EVIDENCE_NOT_READY",
                "The candidate has no complete evaluation evidence.",
            )
        if decision == "approve" and self._active_model_binding_is_configured():
            if not self._run_matches_active_binding(current):
                raise RetrainingControlError(
                    "STALE_ACTIVE_MODEL_BINDING",
                    "The active model changed while this candidate was under review.",
                )
        if decision == "approve":
            self._validate_approval_evidence(current)

        target = {
            "approve": RunState.APPROVED,
            "hold": RunState.HELD,
            "reject": RunState.REJECTED,
        }[decision]
        updated = self._artifact_repository.transition(
            run_id,
            target,
            stage=f"decision_{decision}",
        )
        self._artifact_repository.append_event(
            run_id,
            stage="decision",
            outcome="SUCCESS",
            code=f"CANDIDATE_{decision.upper()}",
            message=reason or "candidate decision recorded",
            actor_id=actor_id,
            actor_role=actor_role,
        )
        return RetrainingDecisionResult(run=updated, decision=decision)

    def _active_model_binding_is_configured(self) -> bool:
        return bool(
            self._active_model_version
            and self._active_model_version != "NOT_AVAILABLE"
            and self._active_model_digest
        )

    def _run_matches_active_binding(self, record: RetrainingRunRecord) -> bool:
        return bool(
            self._active_model_binding_is_configured()
            and record.active_model_version == self._active_model_version
            and record.active_model_digest == self._active_model_digest
        )

    def _read_evidence_artifacts(
        self, record: RetrainingRunRecord
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            evaluation = self._artifact_repository.read_json_artifact(
                record.run_id, "stages/evaluation.json"
            )
            comparison = self._artifact_repository.read_json_artifact(
                record.run_id, "stages/comparison.json"
            )
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "EVIDENCE_NOT_READY",
                "Approval requires a published passing evaluation.",
            ) from exc
        return evaluation, comparison

    def _validate_evidence_binding(
        self,
        record: RetrainingRunRecord,
        evaluation: Mapping[str, Any],
        comparison: Mapping[str, Any],
        *,
        error_code: str = "EVIDENCE_NOT_READY",
    ) -> None:
        if (
            evaluation.get("evidence_status") not in {"NATIVE", "VERIFIED"}
            or evaluation.get("status") != "PASS"
        ):
            raise RetrainingControlError(
                error_code,
                "Approval requires native or verified passing evaluation evidence.",
            )
        provenance = comparison.get("provenance")
        if not isinstance(provenance, Mapping) or any(
            provenance.get(field) != expected
            for field, expected in (
                ("dataset_version", record.dataset_version),
                ("dataset_digest", record.dataset_digest),
                ("evaluation_digest", record.evaluation_digest),
                ("active_model_digest", record.active_model_digest),
                ("candidate_model_digest", record.candidate_model_digest),
            )
        ):
            raise RetrainingControlError(
                error_code,
                "Approval evidence is not bound to this run and active model.",
            )
        if comparison.get("overall_status") != "PASS" or comparison.get(
            "decision_allowed"
        ) is not True:
            raise RetrainingControlError(
                error_code,
                "Approval requires passing comparison gates.",
            )
        gates = comparison.get("gate_results")
        if not isinstance(gates, Mapping) or any(
            not isinstance(gates.get(name), Mapping)
            or gates[name].get("status") != "PASS"
            for name in (
                "active_model_binding",
                "evaluation_binding",
                "evidence",
                "security_regression",
                "quality",
                "improvement",
            )
        ):
            raise RetrainingControlError(
                error_code,
                "Approval requires complete passing evidence gates.",
            )

    def _validate_approval_evidence(self, record: RetrainingRunRecord) -> None:
        evaluation, comparison = self._read_evidence_artifacts(record)
        self._validate_evidence_binding(record, evaluation, comparison)

    def _require_admin(self, actor_id: str, actor_role: str) -> None:
        if actor_role != "ADMIN":
            raise RetrainingControlError(
                "FORBIDDEN", "Administrator review is required.", status_code=403
            )
        if not actor_id.strip() or len(actor_id) > 128:
            raise RetrainingControlError(
                "INVALID_ACTOR", "Reviewer identity is invalid."
            )

    def _load_control_run(self, run_id: str) -> RetrainingRunRecord:
        try:
            return self._artifact_repository.load_run(run_id)
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "RUN_NOT_FOUND", "The retraining run was not found.", status_code=404
            ) from exc

    def _require_staging_adapter(self) -> LocalStagingAdapter:
        if self._staging_adapter is None:
            raise RetrainingControlError(
                "DEPLOYMENT_NOT_AVAILABLE",
                "Local staging deployment is not configured.",
                status_code=501,
            )
        return self._staging_adapter

    @staticmethod
    def _safe_staging_error(exc: StagingDeploymentError) -> tuple[str, str]:
        if "TAMPER" in exc.code or "INTEGRITY" in exc.code:
            return exc.code, "Candidate artifact integrity verification failed."
        if "LOAD" in exc.code or "VERSION_MISMATCH" in exc.code:
            return exc.code, "Local staging model load verification failed."
        if exc.code.startswith("ROLLBACK"):
            return exc.code, "Local staging rollback could not be completed safely."
        return exc.code, "Local staging deployment failed."

    def _mark_recovery_required(
        self,
        run_id: str,
        *,
        stage: str,
        code: str,
        message: str,
        actor_id: str,
        actor_role: str,
    ) -> None:
        """Best-effort durable marker when physical state outruns audit state."""

        try:
            current = self._artifact_repository.load_run(run_id)
            if current.state is not RunState.RECOVERY_REQUIRED:
                self._artifact_repository.transition(
                    run_id,
                    RunState.RECOVERY_REQUIRED,
                    stage=stage,
                    error_code=code,
                    error_message=message,
                )
            try:
                self._append_event(
                    run_id,
                    stage=stage,
                    outcome="WARN",
                    code=code,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    message=message,
                    decision="recovery_required",
                )
            except ArtifactRepositoryError:
                pass
        except (ArtifactRepositoryError, FileNotFoundError, ValueError):
            pass

    def _current_state_or_none(self, run_id: str) -> RunState | None:
        try:
            return self._artifact_repository.load_run(run_id).state
        except (ArtifactRepositoryError, FileNotFoundError, ValueError):
            return None

    def _load_deployment_record(
        self, run_id: str, *, allow_plan: bool = False
    ) -> StagingDeploymentRecord:
        paths = ("staging/deployment.json",)
        if allow_plan:
            paths += ("staging/deployment-plan.json",)
        last_error: Exception | None = None
        for path in paths:
            try:
                payload = self._artifact_repository.read_json_artifact(run_id, path)
                return StagingDeploymentRecord.from_payload(payload)
            except (
                ArtifactRepositoryError,
                FileNotFoundError,
                ValueError,
                StagingDeploymentError,
            ) as exc:
                last_error = exc
        raise RetrainingControlError(
            "DEPLOYMENT_RECORD_INVALID",
            "The local deployment record is missing or invalid.",
        ) from last_error

    def _rollback_is_in_progress(self, run_id: str) -> bool:
        try:
            events = self._artifact_repository.read_events(run_id)
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise ArtifactRepositoryError(
                "rollback event stream is unavailable during recovery"
            ) from exc
        for event in reversed(events):
            code = event.get("code")
            if code == "ROLLBACK_STARTED":
                return True
            if code in {
                "DEPLOY_STARTED",
                "DEPLOY_SUCCEEDED",
                "DEPLOY_FAILED",
                "DEPLOY_ROLLED_BACK",
                "ROLLBACK_SUCCEEDED",
                "ROLLBACK_RECONCILED",
                "DEPLOYMENT_RECONCILED",
            }:
                return False
        return False

    def _validate_deployment_evidence(
        self,
        record: RetrainingRunRecord,
        *,
        expected_candidate_version: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if record.state is not RunState.APPROVED:
            raise RetrainingControlError(
                "RUN_NOT_APPROVED", "Only an approved candidate can be deployed."
            )
        if record.candidate_model_version != expected_candidate_version:
            raise RetrainingControlError(
                "CANDIDATE_VERSION_MISMATCH",
                "The requested candidate does not match the reviewed run.",
            )
        if (
            not self._active_model_binding_is_configured()
            or not self._run_matches_active_binding(record)
        ):
            raise RetrainingControlError(
                "STALE_ACTIVE_MODEL_BINDING",
                "The active model changed since this candidate was reviewed.",
            )
        if not (
            record.candidate_model_version
            and record.candidate_model_digest
            and record.evaluation_digest
            and self._active_model_input_version
        ):
            raise RetrainingControlError(
                "EVIDENCE_NOT_READY",
                "The candidate has incomplete deployment evidence.",
            )
        evaluation, comparison = self._read_evidence_artifacts(record)
        self._validate_evidence_binding(
            record,
            evaluation,
            comparison,
            error_code="DEPLOY_GATE_FAILED",
        )
        return evaluation, comparison

    def _append_event(
        self,
        run_id: str,
        *,
        stage: str,
        outcome: str,
        code: str,
        actor_id: str,
        actor_role: str,
        message: str,
        candidate_model_version: str | None = None,
        candidate_model_digest: str | None = None,
        active_model_digest: str | None = None,
        previous_staging_version: str | None = None,
        decision: str | None = None,
    ) -> None:
        self._artifact_repository.append_event(
            run_id,
            stage=stage,
            outcome=outcome,
            code=code,
            message=message,
            actor_id=actor_id,
            actor_role=actor_role,
            candidate_model_version=candidate_model_version,
            candidate_model_digest=candidate_model_digest,
            active_model_digest=active_model_digest,
            previous_staging_version=previous_staging_version,
            decision=decision,
        )

    def deploy(
        self,
        *,
        run_id: str,
        expected_candidate_version: str,
        actor_id: str,
        actor_role: str,
    ) -> RetrainingRunRecord:
        self._require_admin(actor_id, actor_role)
        record = self._load_control_run(run_id)
        try:
            self._validate_deployment_evidence(
                record, expected_candidate_version=expected_candidate_version
            )
        except RetrainingControlError:
            if record.state is RunState.APPROVED:
                self._append_event(
                    run_id,
                    stage="deployment",
                    outcome="WARN",
                    code="DEPLOY_GATE_REFUSED",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    message="candidate deployment gates refused the operation",
                    candidate_model_version=record.candidate_model_version,
                    candidate_model_digest=record.candidate_model_digest,
                    active_model_digest=self._active_model_digest,
                    decision="approve",
                )
            raise
        adapter = self._require_staging_adapter()
        activation_completed = False
        try:
            plan = adapter.prepare_deployment(
                artifact_root=self._artifact_repository.root,
                run_id=run_id,
                candidate_model_version=record.candidate_model_version or "",
                candidate_model_digest=record.candidate_model_digest or "",
                active_model_version=self._active_model_version,
                active_model_digest=self._active_model_digest or "",
                expected_preprocessing_version=self._active_model_input_version or "",
            )
            self._artifact_repository.publish_json_artifact(
                run_id,
                "staging/deployment-plan.json",
                plan.record.to_payload(),
                stage="deployment_plan",
            )
            self._artifact_repository.transition(
                run_id, RunState.DEPLOYING, stage="deploying"
            )
            self._append_event(
                run_id,
                stage="deployment",
                outcome="STARTED",
                code="DEPLOY_STARTED",
                actor_id=actor_id,
                actor_role=actor_role,
                message="explicit local staging deployment started",
                candidate_model_version=plan.record.candidate_model_version,
                candidate_model_digest=plan.record.candidate_model_digest,
                active_model_digest=plan.record.active_model_digest,
                previous_staging_version=plan.record.previous_staging_version,
                decision="approve",
            )
            adapter_record = adapter.deploy(plan)
            activation_completed = True
            self._artifact_repository.publish_json_artifact(
                run_id,
                "staging/deployment.json",
                adapter_record.to_payload(),
                stage="deployment_result",
            )
            deployed = self._artifact_repository.transition(
                run_id, RunState.DEPLOYED, stage="deployed"
            )
            self._append_event(
                run_id,
                stage="deployment",
                outcome="SUCCESS",
                code="DEPLOY_SUCCEEDED",
                actor_id=actor_id,
                actor_role=actor_role,
                message="candidate explicitly activated in local staging",
            )
            return deployed
        except StagingDeploymentError as exc:
            code, message = self._safe_staging_error(exc)
            try:
                current = self._artifact_repository.load_run(run_id)
            except (
                ArtifactRepositoryError,
                FileNotFoundError,
                ValueError,
            ) as record_exc:
                raise RetrainingControlError(
                    "DEPLOYMENT_RECORD_FAILED",
                    "Local deployment state could not be recorded safely.",
                ) from record_exc
            target: RunState | None = None
            if current.state is RunState.APPROVED:
                try:
                    self._append_event(
                        run_id,
                        stage="deployment",
                        outcome="WARN",
                        code="DEPLOY_PREFLIGHT_FAILED",
                        actor_id=actor_id,
                        actor_role=actor_role,
                        message="candidate deployment preflight was refused",
                        candidate_model_version=current.candidate_model_version,
                        candidate_model_digest=current.candidate_model_digest,
                        active_model_digest=self._active_model_digest,
                        decision="approve",
                    )
                except ArtifactRepositoryError as record_exc:
                    raise RetrainingControlError(
                        "DEPLOYMENT_RECORD_FAILED",
                        "Local deployment state could not be recorded safely.",
                    ) from record_exc
            if current.state is RunState.DEPLOYING:
                target = (
                    RunState.ROLLED_BACK
                    if exc.rolled_back
                    else RunState.RECOVERY_REQUIRED
                    if "RECOVERY" in exc.code or "ROLLBACK_FAILED" in exc.code
                    else RunState.FAILED
                )
                try:
                    self._artifact_repository.transition(
                        run_id,
                        target,
                        stage=(
                            "deploy_rolled_back"
                            if exc.rolled_back
                            else "deploy_recovery_required"
                            if target is RunState.RECOVERY_REQUIRED
                            else "deploy_failed"
                        ),
                        error_code=code,
                        error_message=message,
                    )
                    self._append_event(
                        run_id,
                        stage="deployment",
                        outcome="WARN" if exc.rolled_back else "FAIL",
                        code=(
                            "DEPLOY_ROLLED_BACK"
                            if exc.rolled_back
                            else "DEPLOY_RECOVERY_REQUIRED"
                            if target is RunState.RECOVERY_REQUIRED
                            else "DEPLOY_FAILED"
                        ),
                        actor_id=actor_id,
                        actor_role=actor_role,
                        message=(
                            "candidate deployment failed; known-good staging was "
                            "restored"
                            if exc.rolled_back
                            else "local staging deployment requires recovery"
                            if target is RunState.RECOVERY_REQUIRED
                            else "local staging deployment failed"
                        ),
                    )
                except ArtifactRepositoryError as record_exc:
                    self._mark_recovery_required(
                        run_id,
                        stage="deploy_recovery_required",
                        code="DEPLOYMENT_RECOVERY_REQUIRED",
                        message="local staging state requires durable recovery",
                        actor_id=actor_id,
                        actor_role=actor_role,
                    )
                    raise RetrainingControlError(
                        "DEPLOYMENT_RECOVERY_REQUIRED",
                        "Local staging state requires explicit recovery.",
                    ) from record_exc
            if target is RunState.RECOVERY_REQUIRED:
                raise RetrainingControlError(
                    "DEPLOYMENT_RECOVERY_REQUIRED",
                    "Local staging state requires explicit recovery.",
                ) from exc
            raise RetrainingControlError(code, message) from exc
        except ArtifactRepositoryError as exc:
            if activation_completed:
                self._mark_recovery_required(
                    run_id,
                    stage="deploy_recovery_required",
                    code="DEPLOYMENT_RECOVERY_REQUIRED",
                    message="local staging changed before audit state was recorded",
                    actor_id=actor_id,
                    actor_role=actor_role,
                )
                raise RetrainingControlError(
                    "DEPLOYMENT_RECOVERY_REQUIRED",
                    "Local staging state requires explicit recovery.",
                ) from exc
            try:
                current = self._artifact_repository.load_run(run_id)
            except (ArtifactRepositoryError, FileNotFoundError, ValueError) as record_exc:
                self._mark_recovery_required(
                    run_id,
                    stage="deploy_recovery_required",
                    code="DEPLOYMENT_RECOVERY_REQUIRED",
                    message="local deployment audit state requires recovery",
                    actor_id=actor_id,
                    actor_role=actor_role,
                )
                raise RetrainingControlError(
                    "DEPLOYMENT_RECOVERY_REQUIRED",
                    "Local staging state requires explicit recovery.",
                ) from record_exc
            if current.state is RunState.DEPLOYING:
                try:
                    self._artifact_repository.transition(
                        run_id,
                        RunState.APPROVED,
                        stage="deployment_audit_failed_before_activation",
                        error_code="DEPLOYMENT_RECORD_FAILED",
                        error_message="Local deployment audit state could not be recorded.",
                    )
                except ArtifactRepositoryError as restore_exc:
                    self._mark_recovery_required(
                        run_id,
                        stage="deploy_recovery_required",
                        code="DEPLOYMENT_RECOVERY_REQUIRED",
                        message="local deployment audit state requires recovery",
                        actor_id=actor_id,
                        actor_role=actor_role,
                    )
                    raise RetrainingControlError(
                        "DEPLOYMENT_RECOVERY_REQUIRED",
                        "Local staging state requires explicit recovery.",
                    ) from restore_exc
            raise RetrainingControlError(
                "DEPLOYMENT_RECORD_FAILED",
                "Local deployment audit state could not be recorded.",
            ) from exc

    def rollback(
        self,
        *,
        run_id: str,
        previous_staging_version: str,
        reason: str,
        actor_id: str,
        actor_role: str,
    ) -> RetrainingRunRecord:
        self._require_admin(actor_id, actor_role)
        if not reason.strip() or len(reason) > 500:
            raise RetrainingControlError(
                "REASON_REQUIRED", "A rollback reason is required."
            )
        if any(
            marker in reason
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise RetrainingControlError(
                "INVALID_REASON", "Rollback reason contains forbidden content."
            )
        record = self._load_control_run(run_id)
        if record.state not in {
            RunState.DEPLOYED,
            RunState.DEPLOYING,
            RunState.RECOVERY_REQUIRED,
        }:
            raise RetrainingControlError(
                "RUN_NOT_DEPLOYED", "Only a deployed candidate can be rolled back."
            )
        adapter = self._require_staging_adapter()
        deployment = self._load_deployment_record(
            run_id,
            allow_plan=record.state
            in {RunState.DEPLOYING, RunState.RECOVERY_REQUIRED},
        )
        allowed_statuses = (
            {"DEPLOYED"}
            if record.state is RunState.DEPLOYED
            else {"PREPARED", "DEPLOYED"}
        )
        if deployment.run_id != run_id or deployment.status not in allowed_statuses:
            raise RetrainingControlError(
                "DEPLOYMENT_RECORD_INVALID",
                "The local deployment record is not bound to this deployed run.",
            )
        if record.state in {RunState.DEPLOYING, RunState.RECOVERY_REQUIRED}:
            try:
                pointer = adapter.read_active_pointer()
            except StagingDeploymentError:
                pointer = None
            if pointer is not None and (
                pointer.model_version == deployment.previous_staging_version
                and pointer.artifact_digest == deployment.previous_staging_digest
            ):
                try:
                    rollback_in_progress = self._rollback_is_in_progress(run_id)
                    if deployment.status == "PREPARED" and not rollback_in_progress:
                        adapter.reconcile_prepared_deployment(deployment)
                        reconciled = self._artifact_repository.transition(
                            run_id,
                            RunState.APPROVED,
                            stage="deployment_reconciled_before_activation",
                            error_code=None,
                            error_message=None,
                        )
                        self._append_event(
                            run_id,
                            stage="deployment",
                            outcome="SUCCESS",
                            code="DEPLOYMENT_RECONCILED",
                            actor_id=actor_id,
                            actor_role=actor_role,
                            message=(
                                "known-good staging was active; deployment audit "
                                "state was reconciled"
                            ),
                            decision="recovery",
                        )
                        return reconciled
                    try:
                        reconciled_record = adapter.reconcile_completed_rollback(
                            deployment
                        )
                    except StagingDeploymentError as exc:
                        if exc.code != "ROLLBACK_NOT_COMPLETE":
                            raise
                        reconciled_record = None
                    if reconciled_record is None:
                        # The candidate is still present, so the normal adapter
                        # rollback path can finish an interrupted operation.
                        pass
                    else:
                        self._artifact_repository.publish_json_artifact(
                            run_id,
                            "staging/rollback-recovery-result.json",
                            reconciled_record.to_payload(),
                            stage="rollback_recovery",
                        )
                        reconciled = self._artifact_repository.transition(
                            run_id,
                            RunState.ROLLED_BACK,
                            stage="rollback_reconciled",
                            error_code=None,
                            error_message=None,
                        )
                        self._append_event(
                            run_id,
                            stage="rollback",
                            outcome="SUCCESS",
                            code="ROLLBACK_RECONCILED",
                            actor_id=actor_id,
                            actor_role=actor_role,
                            message=(
                                "known-good staging was active; rollback audit state "
                                "was reconciled"
                            ),
                            decision="recovery",
                        )
                        return reconciled
                except (ArtifactRepositoryError, StagingDeploymentError) as exc:
                    self._mark_recovery_required(
                        run_id,
                        stage="rollback_recovery_required",
                        code="ROLLBACK_RECOVERY_REQUIRED",
                        message="durable recovery reconciliation could not be recorded",
                        actor_id=actor_id,
                        actor_role=actor_role,
                    )
                    raise RetrainingControlError(
                        "ROLLBACK_RECOVERY_REQUIRED",
                        "Local rollback state requires explicit recovery.",
                    ) from exc
        rollback_completed = False
        try:
            self._artifact_repository.transition(
                run_id, RunState.DEPLOYING, stage="rolling_back"
            )
            self._append_event(
                run_id,
                stage="rollback",
                outcome="STARTED",
                code="ROLLBACK_STARTED",
                actor_id=actor_id,
                actor_role=actor_role,
                message="explicit local staging rollback started",
                candidate_model_version=deployment.candidate_model_version,
                candidate_model_digest=deployment.candidate_model_digest,
                active_model_digest=deployment.active_model_digest,
                previous_staging_version=deployment.previous_staging_version,
                decision="rollback",
            )
            rolled_back_record = adapter.rollback(
                deployment,
                requested_previous_version=previous_staging_version,
            )
            rollback_completed = True
            self._artifact_repository.publish_json_artifact(
                run_id,
                "staging/rollback-result.json",
                rolled_back_record.to_payload(),
                stage="rollback_result",
            )
            result = self._artifact_repository.transition(
                run_id, RunState.ROLLED_BACK, stage="rolled_back"
            )
            self._append_event(
                run_id,
                stage="rollback",
                outcome="SUCCESS",
                code="ROLLBACK_SUCCEEDED",
                actor_id=actor_id,
                actor_role=actor_role,
                message="known-good local staging model was restored",
            )
            return result
        except StagingDeploymentError as exc:
            code, message = self._safe_staging_error(exc)
            try:
                current = self._artifact_repository.load_run(run_id)
            except (
                ArtifactRepositoryError,
                FileNotFoundError,
                ValueError,
            ) as record_exc:
                self._mark_recovery_required(
                    run_id,
                    stage="rollback_recovery_required",
                    code="ROLLBACK_RECOVERY_REQUIRED",
                    message="rollback state could not be read after a staging failure",
                    actor_id=actor_id,
                    actor_role=actor_role,
                )
                raise RetrainingControlError(
                    "ROLLBACK_RECOVERY_REQUIRED",
                    "Local rollback state requires explicit recovery.",
                ) from record_exc
            if current.state is RunState.DEPLOYING:
                target = (
                    RunState.RECOVERY_REQUIRED
                    if "RECOVERY" in exc.code
                    else RunState.DEPLOYED
                )
                try:
                    self._artifact_repository.transition(
                        run_id,
                        target,
                        stage=(
                            "rollback_recovery_required"
                            if target is RunState.RECOVERY_REQUIRED
                            else "rollback_failed"
                        ),
                        error_code=code,
                        error_message=message,
                    )
                    self._append_event(
                        run_id,
                        stage="rollback",
                        outcome="WARN",
                        code=(
                            "ROLLBACK_RECOVERY_REQUIRED"
                            if target is RunState.RECOVERY_REQUIRED
                            else "ROLLBACK_FAILED"
                        ),
                        actor_id=actor_id,
                        actor_role=actor_role,
                        message=(
                            "rollback state requires explicit recovery"
                            if target is RunState.RECOVERY_REQUIRED
                            else "rollback failed; deployed candidate remains active"
                        ),
                    )
                except ArtifactRepositoryError as record_exc:
                    self._mark_recovery_required(
                        run_id,
                        stage="rollback_recovery_required",
                        code="ROLLBACK_RECOVERY_REQUIRED",
                        message="rollback state requires durable recovery",
                        actor_id=actor_id,
                        actor_role=actor_role,
                    )
                    raise RetrainingControlError(
                        "ROLLBACK_RECOVERY_REQUIRED",
                        "Local rollback state requires explicit recovery.",
                    ) from record_exc
                if target is RunState.RECOVERY_REQUIRED:
                    raise RetrainingControlError(
                        "ROLLBACK_RECOVERY_REQUIRED",
                        "Local rollback state requires explicit recovery.",
                    ) from exc
            raise RetrainingControlError(code, message) from exc
        except ArtifactRepositoryError as exc:
            current_state = self._current_state_or_none(run_id)
            if rollback_completed or current_state is RunState.DEPLOYING:
                self._mark_recovery_required(
                    run_id,
                    stage="rollback_recovery_required",
                    code="ROLLBACK_RECOVERY_REQUIRED",
                    message=(
                        "local staging changed before rollback audit state was "
                        "recorded"
                    ),
                    actor_id=actor_id,
                    actor_role=actor_role,
                )
                raise RetrainingControlError(
                    "ROLLBACK_RECOVERY_REQUIRED",
                    "Local rollback state requires explicit recovery.",
                ) from exc
            raise RetrainingControlError(
                "ROLLBACK_RECORD_FAILED",
                "Local rollback audit state could not be recorded.",
            ) from exc


__all__ = [
    "RetrainingControlError",
    "RetrainingControlUseCase",
    "RetrainingDecisionResult",
    "RetrainingRunDetail",
    "RetrainingSummarySnapshot",
]
