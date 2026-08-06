"""Validation and quarantine for prepared retraining batches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ml_model.evaluation.golden_controls import GoldenControlSet, find_golden_overlap
from ml_model.retraining.experiment_contract import (
    EXPECTED_LABELS,
    canonical_json_sha256,
    sha256_file,
)

REQUIRED_BATCH_FIELDS = {
    "sample_id",
    "model_input_text",
    "model_input_hash",
    "ground_truth_label",
    "batch_day",
    "source_type",
    "is_synthetic",
    "review_status",
    "provenance_id",
    "preprocessing_version",
}
APPROVED_REVIEW_STATUS = "approved_for_training"


@dataclass
class BatchValidationReport:
    batch_file: str
    input_sha256: str
    accepted_samples: list[dict[str, Any]]
    rejected_samples: list[dict[str, Any]]
    preprocessing_version: str

    @property
    def passed(self) -> bool:
        return not self.rejected_samples

    @property
    def accepted_hash(self) -> str:
        return canonical_json_sha256({"samples": self.accepted_samples})

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_file": self.batch_file,
            "input_sha256": self.input_sha256,
            "accepted_hash": self.accepted_hash,
            "accepted_count": len(self.accepted_samples),
            "rejected_count": len(self.rejected_samples),
            "rejected_samples": self.rejected_samples,
            "preprocessing_version": self.preprocessing_version,
            "passed": self.passed,
        }


def _reject(
    rejected: list[dict[str, Any]],
    *,
    line_number: int,
    sample: Mapping[str, Any] | None,
    reason: str,
) -> None:
    safe_sample = _safe_rejection_sample(sample)
    rejected.append(
        {
            "line_number": line_number,
            "sample_id": sample.get("sample_id") if sample else f"line-{line_number}",
            "reason": reason,
            "sample": safe_sample,
        }
    )


def _safe_rejection_sample(
    sample: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not sample:
        return {}
    summary: dict[str, Any] = {
        "sample_id": sample.get("sample_id"),
        "source_type": sample.get("source_type"),
    }
    text = sample.get("model_input_text")
    if isinstance(text, str):
        summary["model_input_sha256"] = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()
    return summary


def _basic_reasons(
    sample: Mapping[str, Any],
    *,
    expected_preprocessing_version: str,
    expected_batch_day: int | None,
) -> list[str]:
    reasons: list[str] = []
    missing = sorted(REQUIRED_BATCH_FIELDS - set(sample))
    if missing:
        reasons.append(f"missing required fields: {', '.join(missing)}")
    text = sample.get("model_input_text")
    if not isinstance(text, str) or not text.strip():
        reasons.append("missing model_input_text")
    stored_hash = sample.get("model_input_hash")
    if not isinstance(stored_hash, str) or not stored_hash.strip():
        reasons.append("missing model_input_hash")
    elif isinstance(text, str):
        actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if stored_hash != actual_hash:
            reasons.append("model_input_hash does not match model_input_text")
    ground_truth = sample.get("ground_truth_label")
    if not isinstance(ground_truth, str) or not ground_truth.strip():
        reasons.append("missing ground truth")
    elif ground_truth not in EXPECTED_LABELS:
        reasons.append(f"unknown label: {ground_truth}")
    if (
        "predicted_label" in sample
        or "prediction" in sample
        or "model_prediction" in sample
    ):
        reasons.append("predicted label cannot be used as ground truth")
    if sample.get("review_status") != APPROVED_REVIEW_STATUS:
        reasons.append("not approved for training")
    provenance = sample.get("provenance_id")
    if not isinstance(provenance, str) or not provenance.strip():
        reasons.append("missing provenance")
    if sample.get("preprocessing_version") != expected_preprocessing_version:
        reasons.append("unknown or mismatched preprocessing version")
    if (
        not isinstance(sample.get("sample_id"), str)
        or not str(sample.get("sample_id")).strip()
    ):
        reasons.append("missing sample_id")
    if (
        not isinstance(sample.get("batch_day"), int)
        or not 1 <= int(sample.get("batch_day", 0)) <= 20
    ):
        reasons.append("batch_day must be an integer from 1 to 20")
    elif expected_batch_day is not None and sample.get("batch_day") != expected_batch_day:
        reasons.append(f"batch_day does not match expected day {expected_batch_day}")
    if (
        not isinstance(sample.get("source_type"), str)
        or not str(sample.get("source_type")).strip()
    ):
        reasons.append("missing source_type")
    if not isinstance(sample.get("is_synthetic"), bool):
        reasons.append("is_synthetic must be boolean")
    return reasons


def validate_batch_file(
    batch_path: Path | str,
    *,
    expected_preprocessing_version: str,
    golden_texts: Iterable[str] | None = None,
    golden_controls: GoldenControlSet | None = None,
    expected_batch_day: int | None = None,
    quarantine_dir: Path | str,
) -> BatchValidationReport:
    batch_path = Path(batch_path).expanduser().resolve()
    if not batch_path.is_file():
        raise FileNotFoundError(f"prepared batch does not exist: {batch_path}")
    lines = batch_path.read_text(encoding="utf-8").splitlines()
    accepted_candidates: list[tuple[int, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            _reject(
                rejected,
                line_number=line_number,
                sample=None,
                reason="blank JSONL line",
            )
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            _reject(
                rejected, line_number=line_number, sample=None, reason="invalid JSON"
            )
            continue
        if not isinstance(payload, dict):
            _reject(
                rejected,
                line_number=line_number,
                sample=None,
                reason="sample must be an object",
            )
            continue
        reasons = _basic_reasons(
            payload,
            expected_preprocessing_version=expected_preprocessing_version,
            expected_batch_day=expected_batch_day,
        )
        if reasons:
            _reject(
                rejected,
                line_number=line_number,
                sample=payload,
                reason="; ".join(reasons),
            )
        else:
            accepted_candidates.append((line_number, dict(payload)))

    invalid_lines: set[int] = set()
    if golden_controls is not None:
        overlaps = find_golden_overlap(
            golden_controls,
            [sample for _, sample in accepted_candidates],
            near_duplicate_threshold=0.90,
        )
        overlap_by_id = {item["sample_id"]: item for item in overlaps}
        for line_number, sample in accepted_candidates:
            overlap = overlap_by_id.get(sample["sample_id"])
            if overlap is not None:
                invalid_lines.add(line_number)
                _reject(
                    rejected,
                    line_number=line_number,
                    sample=sample,
                    reason=f"golden overlap: {overlap['matches']}",
                )
    else:
        golden_text_set = set(golden_texts or ())
        for line_number, sample in accepted_candidates:
            if sample["model_input_text"] in golden_text_set:
                invalid_lines.add(line_number)
                _reject(
                    rejected,
                    line_number=line_number,
                    sample=sample,
                    reason="golden overlap",
                )

    by_text: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for line_number, sample in accepted_candidates:
        by_text.setdefault(str(sample["model_input_text"]), []).append(
            (line_number, sample)
        )
    for entries in by_text.values():
        if len(entries) > 1:
            labels = {entry[1]["ground_truth_label"] for entry in entries}
            reason = (
                "conflicting label for exact duplicate"
                if len(labels) > 1
                else "exact duplicate sample"
            )
            for line_number, sample in entries:
                invalid_lines.add(line_number)
                _reject(rejected, line_number=line_number, sample=sample, reason=reason)

    accepted = [
        sample
        for line_number, sample in accepted_candidates
        if line_number not in invalid_lines
    ]
    accepted.sort(key=lambda row: str(row["sample_id"]))
    rejected.sort(key=lambda row: (int(row["line_number"]), str(row["sample_id"])))
    quarantine_path = Path(quarantine_dir).expanduser().resolve()
    quarantine_path.mkdir(parents=True, exist_ok=True)
    quarantine_file = quarantine_path / f"{batch_path.stem}.quarantine.jsonl"
    quarantine_file.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rejected),
        encoding="utf-8",
    )
    report = BatchValidationReport(
        batch_file=batch_path.name,
        input_sha256=sha256_file(batch_path),
        accepted_samples=accepted,
        rejected_samples=rejected,
        preprocessing_version=expected_preprocessing_version,
    )
    (quarantine_path / f"{batch_path.stem}.validation.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
