"""Deterministic export of approved, immutable review snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.preprocessing.request_similarity import canonicalize_similarity_text
from ml_model.retraining.dashboard_contracts import (
    CANONICAL_LABELS,
    DatasetManifest,
    ExportedSample,
    canonical_json,
    get_run_artifact_directory,
)
from web_app.domain.retraining import (
    RetrainingReviewCandidate,
    RetrainingReviewSummary,
)

EXPORTER_VERSION = "dashboard-export.v1"
APPROVED_REVIEW_STATE = "approved_for_training"
SUPPORTED_SOURCE_PROVENANCE = {
    "CLOUDFLARE_CONNECTING_IP",
    "DIRECT_REMOTE_ADDR",
}
SUPPORTED_SOURCE_VERIFICATION = {"VERIFIED", "UNVERIFIED"}


@dataclass(frozen=True)
class ExportLimits:
    """Safety limits applied before an export can be consumed by a worker."""

    max_total_additions: int = 10_000
    max_per_class_additions: int = 5_000
    max_source_fraction: float = 0.90
    source_concentration_min_samples: int = 10
    max_repeated_normalized_inputs: int = 1
    max_class_distribution_delta: float | None = None
    baseline_class_counts: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_total_additions < 0 or self.max_per_class_additions < 0:
            raise ValueError("export limits cannot be negative")
        if not 0.0 < self.max_source_fraction <= 1.0:
            raise ValueError("max_source_fraction must be within (0, 1]")
        if self.source_concentration_min_samples < 1:
            raise ValueError("source_concentration_min_samples must be positive")
        if self.max_repeated_normalized_inputs < 1:
            raise ValueError("max_repeated_normalized_inputs must be positive")
        if self.max_class_distribution_delta is not None and not (
            0.0 <= self.max_class_distribution_delta <= 1.0
        ):
            raise ValueError("max_class_distribution_delta must be within [0, 1]")
        if any(
            label not in CANONICAL_LABELS or int(count) < 0
            for label, count in self.baseline_class_counts.items()
        ):
            raise ValueError("baseline class counts contain an invalid label/count")

    def to_dict(self) -> dict[str, object]:
        return {
            "max_total_additions": self.max_total_additions,
            "max_per_class_additions": self.max_per_class_additions,
            "max_source_fraction": self.max_source_fraction,
            "source_concentration_min_samples": self.source_concentration_min_samples,
            "max_repeated_normalized_inputs": self.max_repeated_normalized_inputs,
            "max_class_distribution_delta": self.max_class_distribution_delta,
            "baseline_class_counts": {
                label: int(self.baseline_class_counts.get(label, 0))
                for label in sorted(CANONICAL_LABELS)
            },
        }


@dataclass(frozen=True)
class ExportRejection:
    """Safe rejection detail; it never contains model-input text or raw HTTP."""

    sample_id: str
    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "sample_id": self.sample_id,
            "code": self.code,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DashboardExportResult:
    status: str
    samples: tuple[ExportedSample, ...]
    rejections: tuple[ExportRejection, ...]
    manifest: dict[str, object]
    export_path: Path
    manifest_path: Path
    summary: RetrainingReviewSummary


def _iso_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _reject(
    candidate: RetrainingReviewCandidate, code: str, detail: str
) -> ExportRejection:
    return ExportRejection(sample_id=candidate.sample_id, code=code, detail=detail)


def _validate_candidate(
    candidate: RetrainingReviewCandidate,
    *,
    expected_preprocessing_version: str,
) -> tuple[ExportedSample | None, ExportRejection | None]:
    if candidate.approval_state != APPROVED_REVIEW_STATE:
        code = (
            "EXCLUDED_FROM_TRAINING"
            if candidate.approval_state == "excluded_from_training"
            else "INVALID_APPROVAL_STATE"
        )
        return None, _reject(candidate, code, "review is not approved for training")
    if candidate.review_id is None or candidate.review_id < 1:
        return None, _reject(candidate, "INVALID_REVIEW_ID", "review id is missing")
    if candidate.verified_label not in CANONICAL_LABELS:
        return None, _reject(
            candidate, "NON_CANONICAL_LABEL", "verified label is unsupported"
        )
    if not isinstance(candidate.reviewer_id, str) or not candidate.reviewer_id.strip():
        return None, _reject(
            candidate, "UNTRUSTED_REVIEWER", "reviewer identity is missing"
        )
    if len(candidate.reviewer_id) > 128 or any(
        ord(character) < 32 for character in candidate.reviewer_id
    ):
        return None, _reject(
            candidate, "UNTRUSTED_REVIEWER", "reviewer identity is invalid"
        )
    if candidate.reviewer_role not in {"ANALYST", "ADMIN"}:
        return None, _reject(
            candidate, "UNTRUSTED_REVIEWER", "reviewer role is unauthorized"
        )
    if (
        not isinstance(candidate.model_input_text, str)
        or not candidate.model_input_text.strip()
    ):
        return None, _reject(candidate, "MISSING_MODEL_INPUT", "model input is empty")
    expected_hash = hashlib.sha256(
        candidate.model_input_text.encode("utf-8")
    ).hexdigest()
    if candidate.model_input_hash != expected_hash:
        return None, _reject(
            candidate, "HASH_MISMATCH", "model-input hash does not match text"
        )
    if candidate.preprocessing_version != expected_preprocessing_version:
        return None, _reject(
            candidate,
            "UNSUPPORTED_PREPROCESSING",
            "review preprocessing does not match the configured runtime contract",
        )
    if (
        not isinstance(candidate.model_version, str)
        or not candidate.model_version.strip()
    ):
        return None, _reject(
            candidate, "MISSING_PROVENANCE", "model version is missing"
        )
    if candidate.ingest_event_hash is None or len(candidate.ingest_event_hash) != 64:
        return None, _reject(
            candidate, "MISSING_PROVENANCE", "source event hash is missing"
        )
    if candidate.source_provenance not in SUPPORTED_SOURCE_PROVENANCE:
        return None, _reject(
            candidate, "INVALID_SOURCE_PROVENANCE", "source provenance is unsupported"
        )
    if candidate.source_verification_status not in SUPPORTED_SOURCE_VERIFICATION:
        return None, _reject(
            candidate,
            "INVALID_SOURCE_VERIFICATION",
            "source verification is unsupported",
        )
    try:
        reviewed_at = _iso_timestamp(candidate.reviewed_at)
    except AttributeError, TypeError, ValueError:
        return None, _reject(
            candidate, "INVALID_REVIEW_TIMESTAMP", "review timestamp is invalid"
        )
    if (
        candidate.predicted_label is not None
        and candidate.predicted_label not in CANONICAL_LABELS
    ):
        return None, _reject(
            candidate, "NON_CANONICAL_PREDICTION", "prediction metadata is malformed"
        )
    if (
        candidate.prediction_confidence is not None
        and not 0.0 <= candidate.prediction_confidence <= 1.0
    ):
        return None, _reject(
            candidate, "INVALID_PREDICTION_METADATA", "prediction confidence is invalid"
        )
    try:
        sample = ExportedSample(
            sample_id=candidate.sample_id,
            traffic_log_id=candidate.traffic_log_id,
            review_revision=candidate.revision,
            model_input_text=candidate.model_input_text,
            model_input_hash=candidate.model_input_hash,
            verified_label=candidate.verified_label,
            predicted_label=candidate.predicted_label,
            prediction_confidence=candidate.prediction_confidence,
            prediction_confidence_level=candidate.prediction_confidence_level,
            model_version=candidate.model_version,
            preprocessing_version=candidate.preprocessing_version,
            reviewer_id=candidate.reviewer_id,
            reviewed_at=reviewed_at,
            source_provenance=candidate.source_provenance,
            source_verification_status=candidate.source_verification_status,
            ingest_event_hash=candidate.ingest_event_hash,
        )
    except (TypeError, ValueError) as exc:
        return None, _reject(candidate, "INVALID_REVIEW_EVIDENCE", str(exc)[:160])
    return sample, None


def _safety_rejections(
    samples: Sequence[ExportedSample],
    *,
    limits: ExportLimits,
) -> list[ExportRejection]:
    rejections: list[ExportRejection] = []
    total = len(samples)
    if total > limits.max_total_additions:
        rejections.append(
            ExportRejection(
                "__run__",
                "TOTAL_LIMIT_EXCEEDED",
                "total additions exceed the configured limit",
            )
        )
    class_counts = Counter(sample.verified_label for sample in samples)
    if any(count > limits.max_per_class_additions for count in class_counts.values()):
        rejections.append(
            ExportRejection(
                "__run__",
                "CLASS_QUOTA_EXCEEDED",
                "class additions exceed the configured limit",
            )
        )
    source_counts = Counter(sample.source_provenance for sample in samples)
    if total >= limits.source_concentration_min_samples and source_counts:
        highest_fraction = max(source_counts.values()) / total
        if highest_fraction > limits.max_source_fraction:
            rejections.append(
                ExportRejection(
                    "__run__",
                    "SOURCE_CONCENTRATION_LIMIT",
                    "source concentration exceeds the configured limit",
                )
            )
    if limits.max_class_distribution_delta is not None and limits.baseline_class_counts:
        baseline_total = sum(limits.baseline_class_counts.values())
        if baseline_total > 0 and total > 0:
            for label in CANONICAL_LABELS:
                baseline_share = (
                    limits.baseline_class_counts.get(label, 0) / baseline_total
                )
                observed_share = class_counts.get(label, 0) / total
                if (
                    abs(observed_share - baseline_share)
                    > limits.max_class_distribution_delta
                ):
                    rejections.append(
                        ExportRejection(
                            "__run__",
                            "CLASS_DISTRIBUTION_SHIFT",
                            "class distribution change exceeds the configured limit",
                        )
                    )
                    break
    return rejections


def export_dashboard_reviews(
    candidates: Sequence[RetrainingReviewCandidate],
    *,
    run_id: str,
    output_root: Path | str,
    source_dataset_version: str,
    expected_preprocessing_version: str = MODEL_INPUT_VERSION,
    limits: ExportLimits | None = None,
    created_at: datetime | None = None,
    review_summary: RetrainingReviewSummary | None = None,
) -> DashboardExportResult:
    """Validate and write one immutable local export without consuming reviews."""

    configured_limits = limits or ExportLimits()
    sorted_candidates = sorted(
        candidates, key=lambda candidate: (candidate.traffic_log_id, candidate.revision)
    )
    accepted: list[ExportedSample] = []
    rejections: list[ExportRejection] = []
    seen_sample_ids: set[str] = set()
    normalized_counts: Counter[str] = Counter()
    for candidate in sorted_candidates:
        if candidate.sample_id in seen_sample_ids:
            rejections.append(
                _reject(candidate, "DUPLICATE_REVIEW", "review candidate is repeated")
            )
            continue
        seen_sample_ids.add(candidate.sample_id)
        sample, rejection = _validate_candidate(
            candidate, expected_preprocessing_version=expected_preprocessing_version
        )
        if rejection is not None:
            rejections.append(rejection)
            continue
        assert sample is not None
        normalized_hash = hashlib.sha256(
            canonicalize_similarity_text(sample.model_input_text).encode("utf-8")
        ).hexdigest()
        if (
            normalized_counts[normalized_hash]
            >= configured_limits.max_repeated_normalized_inputs
        ):
            rejections.append(
                _reject(
                    candidate,
                    "DUPLICATE_MODEL_INPUT",
                    "normalized model input was already accepted",
                )
            )
            continue
        normalized_counts[normalized_hash] += 1
        accepted.append(sample)

    safety_rejections = _safety_rejections(accepted, limits=configured_limits)
    rejections.extend(safety_rejections)
    approved_candidates = sum(
        candidate.approval_state == APPROVED_REVIEW_STATE
        for candidate in sorted_candidates
    )
    if review_summary is not None and review_summary.approved > approved_candidates:
        rejections.append(
            ExportRejection(
                "__run__",
                "QUERY_LIMIT_EXCEEDED",
                "bounded review projection was incomplete",
            )
        )
    quarantine = bool(safety_rejections) or any(
        rejection.code == "QUERY_LIMIT_EXCEEDED" for rejection in rejections
    )
    emitted_samples = tuple() if quarantine else tuple(accepted)
    status = (
        "QUARANTINED_FOR_REVIEW"
        if quarantine
        else ("READY" if emitted_samples else "EMPTY")
    )

    created_timestamp = created_at or datetime.now(timezone.utc)
    if created_timestamp.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    run_root = get_run_artifact_directory(output_root, run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    run_dir = run_root / "export"
    temporary_run_dir = run_root / f".export.{uuid.uuid4().hex}.tmp"
    temporary_run_dir.mkdir(exist_ok=False)
    export_content = "".join(
        canonical_json(sample) + "\n" for sample in emitted_samples
    ).encode("utf-8")
    export_checksum = hashlib.sha256(export_content).hexdigest()
    rejection_counts = Counter(rejection.code for rejection in rejections)
    class_counts = Counter(sample.verified_label for sample in emitted_samples)
    base_summary = review_summary or RetrainingReviewSummary(
        approved=sum(
            candidate.approval_state == APPROVED_REVIEW_STATE
            for candidate in sorted_candidates
        ),
        excluded=sum(
            candidate.approval_state == "excluded_from_training"
            for candidate in sorted_candidates
        ),
    )
    summary = replace(
        base_summary,
        invalid=sum(
            rejection.sample_id != "__run__"
            and rejection.code
            not in {
                "EXCLUDED_FROM_TRAINING",
                "DUPLICATE_MODEL_INPUT",
                "DUPLICATE_REVIEW",
            }
            for rejection in rejections
        ),
        duplicate=sum(
            rejection.code in {"DUPLICATE_MODEL_INPUT", "DUPLICATE_REVIEW"}
            for rejection in rejections
        ),
    )
    dataset_manifest = DatasetManifest(
        dataset_version=f"dashboard-export-{run_id}",
        source_dataset_version=source_dataset_version,
        preprocessing_version=expected_preprocessing_version,
        exporter_version=EXPORTER_VERSION,
        created_at=_iso_timestamp(created_timestamp),
        row_count=len(emitted_samples),
        class_counts={
            label: int(class_counts.get(label, 0)) for label in sorted(CANONICAL_LABELS)
        },
        duplicate_count=int(rejection_counts.get("DUPLICATE_MODEL_INPUT", 0)),
        rejected_counts=dict(sorted(rejection_counts.items())),
        source_review_revisions=tuple(
            f"{candidate.traffic_log_id}:{candidate.revision}"
            for candidate in sorted_candidates
        ),
        file_checksums={"approved_samples.jsonl": export_checksum},
    )
    manifest: dict[str, object] = {
        "manifest_version": "dashboard-export.v1",
        "run_id": run_id,
        "status": status,
        "created_at": dataset_manifest.created_at,
        "source_dataset_version": source_dataset_version,
        "preprocessing_version": expected_preprocessing_version,
        "exporter_version": EXPORTER_VERSION,
        "row_count": len(emitted_samples),
        "class_counts": dataset_manifest.class_counts,
        "source_review_ids": [
            int(candidate.review_id)
            for candidate in sorted_candidates
            if candidate.review_id is not None
        ],
        "source_review_revisions": list(dataset_manifest.source_review_revisions),
        "input_hashes": [sample.model_input_hash for sample in emitted_samples],
        "verified_labels": [sample.verified_label for sample in emitted_samples],
        "rejected_counts": dataset_manifest.rejected_counts,
        "rejections": [rejection.to_dict() for rejection in rejections],
        "duplicate_count": dataset_manifest.duplicate_count,
        "limits": configured_limits.to_dict(),
        "observed": {
            "total_additions": len(accepted),
            "class_counts": dict(
                sorted(Counter(sample.verified_label for sample in accepted).items())
            ),
            "source_counts": dict(
                sorted(Counter(sample.source_provenance for sample in accepted).items())
            ),
        },
        "files": dataset_manifest.file_checksums,
        "dataset_manifest": dataset_manifest.to_dict(),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        canonical_json(manifest).encode("utf-8")
    ).hexdigest()
    temporary_export_path = temporary_run_dir / "approved_samples.jsonl"
    temporary_manifest_path = temporary_run_dir / "export_manifest.json"
    try:
        temporary_export_path.write_bytes(export_content)
        temporary_manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary_run_dir, run_dir)
    except BaseException as exc:
        if temporary_run_dir.exists():
            shutil.rmtree(temporary_run_dir)
        if isinstance(exc, PermissionError) and run_dir.exists():
            raise FileExistsError(f"export already exists: {run_dir}") from exc
        raise
    export_path = run_dir / "approved_samples.jsonl"
    manifest_path = run_dir / "export_manifest.json"
    return DashboardExportResult(
        status=status,
        samples=emitted_samples,
        rejections=tuple(rejections),
        manifest=manifest,
        export_path=export_path,
        manifest_path=manifest_path,
        summary=summary,
    )


__all__ = [
    "DashboardExportResult",
    "EXPORTER_VERSION",
    "ExportLimits",
    "ExportRejection",
    "export_dashboard_reviews",
]
