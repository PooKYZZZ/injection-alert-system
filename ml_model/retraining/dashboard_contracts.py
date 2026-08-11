"""Serializable contracts shared by the local model-operations pipeline.

The records in this module intentionally do not depend on the web application's
ORM or presentation schemas.  They are the durable boundary between the
approved-review exporter, the local worker, and the dashboard/BFF layers.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

CANONICAL_LABELS = (
    "Code Injection",
    "Normal",
    "Other Attacks",
    "SQL Injection",
)
METRIC_VALUE_TOLERANCE = 1e-9
DEFAULT_RETRAINING_RESULTS_ROOT = Path("ml_model/results/dashboard_retraining")
DATASET_MANIFEST_VERSION = "dashboard-dataset.v1"
RUN_ID_PATTERN = re.compile(r"^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_REASON_LENGTH = 500


class ContractValidationError(ValueError):
    """Raised when a dashboard/retraining contract is malformed."""


class ArtifactLayoutError(ContractValidationError):
    """Raised when a run path is not part of the configured run root."""


class _ValueEnum(str, Enum):
    @classmethod
    def parse(cls, value: str | Enum) -> "_ValueEnum":
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except (TypeError, ValueError) as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ContractValidationError(
                f"invalid {cls.__name__.lower()} '{value}'; expected one of: {allowed}"
            ) from exc


class RunState(_ValueEnum):
    QUEUED = "queued"
    EXPORTING = "exporting"
    DATASET_VALIDATED = "dataset_validated"
    TRAINING = "training"
    EVALUATING = "evaluating"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    HELD = "held"
    REJECTED = "rejected"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    QUARANTINED_FOR_REVIEW = "QUARANTINED_FOR_REVIEW"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    SKIPPED_NO_APPROVED_DATA = "SKIPPED_NO_APPROVED_DATA"


class DecisionValue(_ValueEnum):
    APPROVE = "approve"
    HOLD = "hold"
    REJECT = "reject"


class GateStatus(_ValueEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"


class EvidenceStatus(_ValueEnum):
    VERIFIED = "VERIFIED"
    NATIVE = "NATIVE"
    CONTROLLED_SMOKE = "CONTROLLED_SMOKE"
    PROXY = "PROXY"
    NOT_RUN = "NOT_RUN"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    INVALID = "INVALID"


class MetricKind(_ValueEnum):
    GROUND_TRUTH = "ground_truth"
    PROXY = "proxy"
    CONTROLLED_SMOKE = "controlled_smoke"
    NATIVE_EVALUATION = "native_evaluation"


def _as_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        rendered = value.astimezone(timezone.utc).isoformat()
        return rendered.replace("+00:00", "Z")
    if is_dataclass(value):
        return {
            field.name: _as_primitive(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _as_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_as_primitive(item) for item in value]
    if isinstance(value, set):
        return sorted(_as_primitive(item) for item in value)
    return value


def canonical_json(value: Any) -> str:
    """Return stable JSON suitable for manifest hashes and audit artifacts."""

    return json.dumps(
        _as_primitive(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def is_valid_run_id(run_id: str) -> bool:
    return isinstance(run_id, str) and RUN_ID_PATTERN.fullmatch(run_id) is not None


def build_run_id(created_at: datetime, *, entropy: str | None = None) -> str:
    """Build the stable, filesystem-safe identifier used by a retraining run."""

    if created_at.tzinfo is None:
        raise ContractValidationError("created_at must be timezone-aware")
    utc_time = created_at.astimezone(timezone.utc)
    timestamp = utc_time.strftime("%Y%m%dT%H%M%SZ")
    salt = entropy if entropy is not None else uuid.uuid4().hex
    suffix = hashlib.sha256(f"{timestamp}:{salt}".encode("utf-8")).hexdigest()[:12]
    return f"retrain-{timestamp}-{suffix}"


def _require_digest(value: str, field_name: str) -> None:
    if not isinstance(value, str) or DIGEST_PATTERN.fullmatch(value) is None:
        raise ContractValidationError(
            f"{field_name} must be a 64-character SHA-256 digest"
        )


def get_run_artifact_directory(root: Path | str, run_id: str) -> Path:
    """Resolve one run directory beneath a server-configured artifact root."""

    if not is_valid_run_id(run_id):
        raise ArtifactLayoutError("run_id is not a valid retraining run identifier")
    root_path = Path(root).expanduser().resolve()
    candidate = (root_path / run_id).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise ArtifactLayoutError(
            "run artifact path escapes the configured root"
        ) from exc
    if candidate.parent != root_path:
        raise ArtifactLayoutError(
            "run artifact path must be a direct child of the configured root"
        )
    return candidate


class SerializableContract:
    """Small JSON boundary shared by all immutable contract records."""

    def to_dict(self) -> dict[str, Any]:
        return _as_primitive(self)


@dataclass(frozen=True, slots=True)
class ConfidenceInterval(SerializableContract):
    lower: float
    upper: float
    confidence_level: float = 0.95

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.lower, self.upper, self.confidence_level)
        ):
            raise ContractValidationError("confidence interval values must be finite")
        if self.lower > self.upper:
            raise ContractValidationError(
                "confidence interval lower bound exceeds upper bound"
            )
        if not 0.0 < self.confidence_level < 1.0:
            raise ContractValidationError(
                "confidence level must be between zero and one"
            )


@dataclass(frozen=True, slots=True)
class MetricDefinition(SerializableContract):
    """A metric value together with the evidence needed to interpret it."""

    name: str
    value: float | None
    numerator: int | float | None
    denominator: int | None
    numerator_definition: str
    denominator_definition: str
    ground_truth_source: str
    evaluation_split: str
    support_count: int | None
    evidence_status: EvidenceStatus
    metric_kind: MetricKind
    confidence_interval: ConfidenceInterval | None = None
    evaluation_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            evidence_status = EvidenceStatus.parse(self.evidence_status)
            metric_kind = MetricKind.parse(self.metric_kind)
        except ContractValidationError:
            raise
        object.__setattr__(self, "evidence_status", evidence_status)
        object.__setattr__(self, "metric_kind", metric_kind)
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContractValidationError("metric name is required")
        for value, field_name in (
            (self.numerator, "metric numerator"),
            (self.denominator, "metric denominator"),
            (self.support_count, "metric support"),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise ContractValidationError(f"{field_name} must be an integer")
            if value is not None and value < 0:
                raise ContractValidationError(f"{field_name} cannot be negative")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ContractValidationError(
                "metric numerator cannot exceed its denominator"
            )
        if (
            not isinstance(self.evaluation_split, str)
            or not self.evaluation_split.strip()
        ):
            raise ContractValidationError("metric evaluation split is required")
        if self.evaluation_digest is not None:
            _require_digest(self.evaluation_digest, "evaluation digest")
        if self.value is not None:
            if not isinstance(self.value, (int, float)) or isinstance(
                self.value, bool
            ) or not math.isfinite(self.value) or not 0.0 <= self.value <= 1.0:
                raise ContractValidationError("metric value must be a finite fraction")
            if self.numerator is not None and self.denominator is not None:
                if self.denominator == 0 or not math.isclose(
                    self.value,
                    self.numerator / self.denominator,
                    rel_tol=METRIC_VALUE_TOLERANCE,
                    abs_tol=METRIC_VALUE_TOLERANCE,
                ):
                    raise ContractValidationError(
                        "metric value does not match numerator and denominator"
                    )
        if evidence_status in {
            EvidenceStatus.VERIFIED,
            EvidenceStatus.NATIVE,
            EvidenceStatus.CONTROLLED_SMOKE,
        }:
            if self.value is None or not self.denominator or not self.support_count:
                raise ContractValidationError(
                    "passing metric evidence requires a value and positive support"
                )
            if self.evaluation_digest is None:
                raise ContractValidationError(
                    "passing metric evidence requires an evaluation digest"
                )
        if self.denominator is None and self.numerator is not None:
            raise ContractValidationError("metric numerator requires a denominator")
        if (
            evidence_status
            in {
                EvidenceStatus.NOT_RUN,
                EvidenceStatus.NOT_ENOUGH_EVIDENCE,
                EvidenceStatus.INVALID,
            }
            and self.value is not None
        ):
            raise ContractValidationError(
                "unavailable metric evidence cannot contain a passing value"
            )
        if metric_kind is MetricKind.PROXY and evidence_status not in {
            EvidenceStatus.PROXY,
            EvidenceStatus.NOT_RUN,
            EvidenceStatus.NOT_ENOUGH_EVIDENCE,
            EvidenceStatus.INVALID,
        }:
            raise ContractValidationError(
                "proxy metrics must carry PROXY evidence status"
            )
        if (
            evidence_status is EvidenceStatus.PROXY
            and metric_kind is not MetricKind.PROXY
        ):
            raise ContractValidationError(
                "PROXY evidence cannot be presented as ground truth"
            )
        if metric_kind is MetricKind.GROUND_TRUTH and self.ground_truth_source != (
            "verified_label"
        ):
            raise ContractValidationError(
                "ground-truth metrics must identify verified_label evidence"
            )

    def to_dict(self) -> dict[str, Any]:
        return _as_primitive(self)


@dataclass(frozen=True, slots=True)
class ModelReference(SerializableContract):
    version: str
    digest: str

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ContractValidationError("model version is required")
        _require_digest(self.digest, "model digest")


@dataclass(frozen=True, slots=True)
class EvaluationProvenance(SerializableContract):
    dataset_version: str
    dataset_digest: str
    evaluation_digest: str
    evaluation_split: str
    active_model_digest: str
    candidate_model_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "dataset_digest",
            "evaluation_digest",
            "active_model_digest",
            "candidate_model_digest",
        ):
            _require_digest(getattr(self, field_name), field_name)
        if not self.dataset_version.strip() or not self.evaluation_split.strip():
            raise ContractValidationError(
                "evaluation provenance versions and split are required"
            )


@dataclass(frozen=True, slots=True)
class ExportedSample(SerializableContract):
    """Training-safe sample metadata; raw request payloads do not belong here."""

    sample_id: str
    traffic_log_id: int
    review_revision: int
    model_input_text: str
    model_input_hash: str
    verified_label: str
    predicted_label: str | None
    prediction_confidence: float | None
    prediction_confidence_level: str | None
    model_version: str | None
    preprocessing_version: str
    reviewer_id: str
    # These fields are optional for backwards-compatible contract consumers;
    # the dashboard exporter always populates them from the immutable review.
    reviewed_at: str | None = None
    source_provenance: str | None = None
    source_verification_status: str | None = None
    ingest_event_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.sample_id.strip() or not self.model_input_text.strip():
            raise ContractValidationError(
                "sample id and sanitized model input are required"
            )
        if self.traffic_log_id < 1 or self.review_revision < 1:
            raise ContractValidationError(
                "traffic log id and review revision must be positive"
            )
        _require_digest(self.model_input_hash, "model input hash")
        if self.verified_label not in CANONICAL_LABELS:
            raise ContractValidationError(
                "verified_label must be one of the canonical labels"
            )
        if (
            self.predicted_label is not None
            and self.predicted_label not in CANONICAL_LABELS
        ):
            raise ContractValidationError(
                "predicted_label must be canonical when present"
            )
        if (
            self.prediction_confidence is not None
            and not 0.0 <= self.prediction_confidence <= 1.0
        ):
            raise ContractValidationError(
                "prediction confidence must be between zero and one"
            )
        if not self.preprocessing_version.strip() or not self.reviewer_id.strip():
            raise ContractValidationError(
                "preprocessing version and reviewer id are required"
            )
        for field_name in (
            "reviewed_at",
            "source_provenance",
            "source_verification_status",
        ):
            value = getattr(self, field_name)
            if value is not None and not str(value).strip():
                raise ContractValidationError(f"{field_name} cannot be blank")
        if self.ingest_event_hash is not None:
            _require_digest(self.ingest_event_hash, "ingest event hash")


@dataclass(frozen=True, slots=True)
class RejectionReason(SerializableContract):
    code: str
    count: int

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ContractValidationError("rejection reason code is required")
        if self.count < 1:
            raise ContractValidationError("rejection reason count must be positive")


@dataclass(frozen=True, slots=True)
class DatasetManifest(SerializableContract):
    dataset_version: str
    source_dataset_version: str
    preprocessing_version: str
    exporter_version: str
    created_at: str
    row_count: int
    class_counts: Mapping[str, int]
    duplicate_count: int
    rejected_counts: Mapping[str, int]
    source_review_revisions: tuple[str, ...]
    file_checksums: Mapping[str, str]
    holdout_version: str = "frozen"

    def __post_init__(self) -> None:
        if not self.dataset_version.strip() or not self.preprocessing_version.strip():
            raise ContractValidationError(
                "dataset and preprocessing versions are required"
            )
        if self.row_count < 0 or self.duplicate_count < 0:
            raise ContractValidationError("dataset counts cannot be negative")
        if any(label not in CANONICAL_LABELS for label in self.class_counts):
            raise ContractValidationError(
                "dataset class counts contain an unknown label"
            )
        if any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for count in self.class_counts.values()
        ):
            raise ContractValidationError("dataset class counts cannot be negative")
        if any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for count in self.rejected_counts.values()
        ):
            raise ContractValidationError("dataset rejection counts cannot be negative")
        if sum(self.class_counts.values()) != self.row_count:
            raise ContractValidationError("dataset class counts must equal row_count")
        for checksum_name, checksum in self.file_checksums.items():
            _require_digest(checksum, f"file checksum '{checksum_name}'")


@dataclass(frozen=True, slots=True)
class RunManifest(SerializableContract):
    run_id: str
    state: RunState
    created_at: str
    trigger: str
    requested_by: str
    requested_timezone: str
    dataset_version: str
    dataset_digest: str
    preprocessing_version: str
    active_model_version: str
    active_model_digest: str
    pipeline_version: str
    candidate_model_version: str | None = None
    candidate_model_digest: str | None = None
    evaluation_digest: str | None = None

    def __post_init__(self) -> None:
        if not is_valid_run_id(self.run_id):
            raise ContractValidationError(
                "run_id is not a valid retraining run identifier"
            )
        object.__setattr__(self, "state", RunState.parse(self.state))
        for field_name in ("dataset_digest", "active_model_digest"):
            _require_digest(getattr(self, field_name), field_name)
        for field_name in ("candidate_model_digest", "evaluation_digest"):
            value = getattr(self, field_name)
            if value is not None:
                _require_digest(value, field_name)
        for field_name in (
            "created_at",
            "trigger",
            "requested_by",
            "requested_timezone",
            "dataset_version",
            "preprocessing_version",
            "active_model_version",
            "pipeline_version",
        ):
            if not getattr(self, field_name).strip():
                raise ContractValidationError(f"{field_name} is required")
        if self.candidate_model_version is not None and not isinstance(
            self.candidate_model_version, str
        ):
            raise ContractValidationError("candidate_model_version has invalid type")
        if self.candidate_model_version is not None and not (
            self.candidate_model_version.strip()
        ):
            raise ContractValidationError("candidate_model_version cannot be blank")
        if self.state in {
            RunState.PENDING_APPROVAL,
            RunState.APPROVED,
            RunState.DEPLOYING,
            RunState.DEPLOYED,
            RunState.ROLLED_BACK,
            RunState.RECOVERY_REQUIRED,
        } and (
            not self.candidate_model_version
            or not self.candidate_model_digest
            or not self.evaluation_digest
        ):
            raise ContractValidationError(
                "reviewed run states require candidate and evaluation binding"
            )


@dataclass(frozen=True, slots=True)
class MetricComparison(SerializableContract):
    metric_name: str
    active: MetricDefinition | None
    candidate: MetricDefinition | None
    delta: float | None
    direction: str


@dataclass(frozen=True, slots=True)
class GateResult(SerializableContract):
    name: str
    status: GateStatus
    reason: str
    metric_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", GateStatus.parse(self.status))
        if not self.name.strip() or not self.reason.strip():
            raise ContractValidationError("gate name and reason are required")


@dataclass(frozen=True, slots=True)
class ComparisonResponse(SerializableContract):
    active_model: ModelReference
    candidate_model: ModelReference
    provenance: EvaluationProvenance
    active_metrics: Mapping[str, MetricDefinition]
    candidate_metrics: Mapping[str, MetricDefinition]
    metric_comparisons: Mapping[str, MetricComparison]
    per_class_metrics: Mapping[str, Mapping[str, MetricComparison]]
    gate_results: Mapping[str, GateResult]
    overall_status: GateStatus
    decision_allowed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "overall_status", GateStatus.parse(self.overall_status)
        )
        object.__setattr__(
            self, "active_metrics", MappingProxyType(dict(self.active_metrics))
        )
        object.__setattr__(
            self, "candidate_metrics", MappingProxyType(dict(self.candidate_metrics))
        )
        object.__setattr__(
            self, "metric_comparisons", MappingProxyType(dict(self.metric_comparisons))
        )
        object.__setattr__(
            self,
            "per_class_metrics",
            MappingProxyType(
                {
                    label: MappingProxyType(dict(metrics))
                    for label, metrics in self.per_class_metrics.items()
                }
            ),
        )
        object.__setattr__(
            self, "gate_results", MappingProxyType(dict(self.gate_results))
        )

    def to_dict(self) -> dict[str, Any]:
        return _as_primitive(self)


@dataclass(frozen=True, slots=True)
class ComparisonTolerances(SerializableContract):
    normal_fpr_max_increase: float = 0.001
    attack_escape_max_increase: float = 0.001
    normal_recall_minimum: float = 0.995
    supported_attack_recall_drop: float = 0.01
    macro_f1_max_drop: float = 0.002

    def __post_init__(self) -> None:
        values = (
            self.normal_fpr_max_increase,
            self.attack_escape_max_increase,
            self.normal_recall_minimum,
            self.supported_attack_recall_drop,
            self.macro_f1_max_drop,
        )
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ContractValidationError(
                "comparison tolerances must be finite and non-negative"
            )
        if self.normal_recall_minimum > 1.0:
            raise ContractValidationError("normal recall minimum cannot exceed one")


@dataclass(frozen=True, slots=True)
class Decision(SerializableContract):
    decision: DecisionValue
    run_id: str
    candidate_model_digest: str
    dataset_digest: str
    evaluation_digest: str
    active_model_digest: str
    reviewer_id: str
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision", DecisionValue.parse(self.decision))
        if not is_valid_run_id(self.run_id):
            raise ContractValidationError("decision run_id is invalid")
        for field_name in (
            "candidate_model_digest",
            "dataset_digest",
            "evaluation_digest",
            "active_model_digest",
        ):
            _require_digest(getattr(self, field_name), field_name)
        if not self.reviewer_id.strip():
            raise ContractValidationError("reviewer_id is required")
        if self.reason is not None:
            normalized_reason = self.reason.strip()
            if not normalized_reason or len(normalized_reason) > MAX_REASON_LENGTH:
                raise ContractValidationError(
                    f"reason is required and must be at most "
                    f"{MAX_REASON_LENGTH} characters"
                )
            object.__setattr__(self, "reason", normalized_reason)
        if (
            self.decision in {DecisionValue.HOLD, DecisionValue.REJECT}
            and self.reason is None
        ):
            raise ContractValidationError("hold and reject decisions require a reason")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Decision":
        allowed = {
            "decision",
            "run_id",
            "candidate_model_digest",
            "dataset_digest",
            "evaluation_digest",
            "active_model_digest",
            "reviewer_id",
            "reason",
        }
        if not isinstance(payload, Mapping):
            raise ContractValidationError("decision payload must be an object")
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ContractValidationError(
                f"unknown fields in decision payload: {unknown}"
            )
        missing = sorted(
            field for field in allowed - {"reason"} if field not in payload
        )
        if missing:
            raise ContractValidationError(f"missing decision fields: {missing}")
        if not isinstance(payload.get("reviewer_id"), str):
            raise ContractValidationError("decision payload fields have invalid types")
        if "reason" in payload and payload["reason"] is not None and not isinstance(
            payload["reason"], str
        ):
            raise ContractValidationError("decision payload fields have invalid types")
        try:
            return cls(
                decision=payload["decision"],
                run_id=payload["run_id"],
                candidate_model_digest=payload["candidate_model_digest"],
                dataset_digest=payload["dataset_digest"],
                evaluation_digest=payload["evaluation_digest"],
                active_model_digest=payload["active_model_digest"],
                reviewer_id=payload["reviewer_id"],
                reason=payload.get("reason"),
            )
        except (KeyError, TypeError) as exc:
            raise ContractValidationError(
                "decision payload fields have invalid types"
            ) from exc
