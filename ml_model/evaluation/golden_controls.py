"""Locked golden controls for model and response-action evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ml_model.confidence_tiers import ConfidenceThresholds, classify_confidence
from ml_model.retraining.experiment_contract import (
    EXPECTED_LABELS,
    canonical_json_sha256,
    sha256_file,
)

REQUIRED_CASE_FIELDS = {
    "case_id",
    "model_input_text",
    "expected_label",
    "expected_action",
    "category",
    "source_type",
    "rationale",
    "reviewer",
    "golden_version",
    "locked_at",
}
EXPECTED_ACTIONS = {"ALLOWED", "THROTTLED", "BLOCKED"}


class GoldenControlError(ValueError):
    """Raised when a locked golden set is malformed or tampered with."""


class GoldenOverlapError(GoldenControlError):
    """Raised when a training candidate overlaps a locked golden control."""


@dataclass(frozen=True)
class GoldenCase:
    payload: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    @property
    def model_input_text(self) -> str:
        return str(self.payload["model_input_text"])


@dataclass(frozen=True)
class GoldenControlSet:
    manifest_path: Path
    cases_path: Path
    manifest: dict[str, Any]
    cases: tuple[GoldenCase, ...]

    @property
    def golden_version(self) -> str:
        return str(self.manifest["golden_version"])

    @property
    def texts(self) -> frozenset[str]:
        return frozenset(str(case["model_input_text"]) for case in self.cases)

    def assert_no_overlap(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        near_duplicate_threshold: float = 0.90,
    ) -> None:
        overlaps = find_golden_overlap(
            self,
            rows,
            near_duplicate_threshold=near_duplicate_threshold,
        )
        if overlaps:
            raise GoldenOverlapError(
                f"training data overlaps locked golden controls: {overlaps}"
            )


@dataclass(frozen=True)
class GoldenEvaluation:
    passed: bool
    cases: tuple[dict[str, Any], ...]
    category_results: dict[str, dict[str, Any]]
    mandatory_failures: list[str]
    manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "cases": list(self.cases),
            "category_results": self.category_results,
            "mandatory_failures": list(self.mandatory_failures),
            "manifest_sha256": self.manifest_sha256,
        }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoldenControlError(f"invalid JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise GoldenControlError(f"expected JSON object: {path}")
    return payload


def _validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "manifest_version",
        "golden_version",
        "cases_file",
        "cases_sha256",
        "case_count",
        "manifest_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise GoldenControlError(f"golden manifest is missing fields: {missing}")
    stored_hash = manifest.get("manifest_sha256")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if stored_hash != canonical_json_sha256(unsigned):
        raise GoldenControlError("golden manifest hash mismatch")
    if (
        not isinstance(manifest["cases_sha256"], str)
        or len(manifest["cases_sha256"]) != 64
    ):
        raise GoldenControlError("golden cases hash is invalid")
    if not isinstance(manifest["case_count"], int) or manifest["case_count"] < 1:
        raise GoldenControlError("golden case_count must be a positive integer")


def _validate_case(case: Mapping[str, Any], *, golden_version: str) -> dict[str, Any]:
    missing = sorted(REQUIRED_CASE_FIELDS - set(case))
    if missing:
        raise GoldenControlError(f"golden case is missing fields: {missing}")
    normalized = {key: case[key] for key in REQUIRED_CASE_FIELDS}
    for field in (
        "case_id",
        "model_input_text",
        "category",
        "source_type",
        "rationale",
        "reviewer",
        "locked_at",
    ):
        if not isinstance(normalized[field], str) or not normalized[field].strip():
            raise GoldenControlError(f"golden case {field} must be non-empty")
    if normalized["expected_label"] not in EXPECTED_LABELS:
        raise GoldenControlError(
            f"unknown golden expected label: {normalized['expected_label']}"
        )
    if normalized["expected_action"] not in EXPECTED_ACTIONS:
        raise GoldenControlError(
            f"unknown golden expected action: {normalized['expected_action']}"
        )
    if normalized["golden_version"] != golden_version:
        raise GoldenControlError("golden case version does not match manifest")
    return dict(case)


def load_golden_controls(manifest_path: Path | str) -> GoldenControlSet:
    manifest_path = Path(manifest_path).expanduser().resolve()
    manifest = _load_json(manifest_path)
    _validate_manifest(manifest)
    cases_path = (manifest_path.parent / str(manifest["cases_file"])).resolve()
    if not cases_path.is_file():
        raise GoldenControlError(f"golden cases file does not exist: {cases_path}")
    if sha256_file(cases_path) != manifest["cases_sha256"]:
        raise GoldenControlError("golden cases hash mismatch")
    cases: list[GoldenCase] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    for line_number, line in enumerate(
        cases_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoldenControlError(
                f"invalid golden JSONL at line {line_number}"
            ) from exc
        if not isinstance(payload, dict):
            raise GoldenControlError(
                f"golden case at line {line_number} is not an object"
            )
        case = _validate_case(payload, golden_version=str(manifest["golden_version"]))
        if case["case_id"] in seen_ids or case["model_input_text"] in seen_texts:
            raise GoldenControlError("golden cases contain duplicate IDs or texts")
        seen_ids.add(case["case_id"])
        seen_texts.add(case["model_input_text"])
        cases.append(GoldenCase(case))
    if len(cases) != manifest["case_count"]:
        raise GoldenControlError("golden case_count does not match cases file")
    return GoldenControlSet(manifest_path, cases_path, manifest, tuple(cases))


def _normalized_text(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def find_golden_overlap(
    controls: GoldenControlSet,
    rows: Iterable[Mapping[str, Any]],
    *,
    near_duplicate_threshold: float = 0.90,
) -> list[dict[str, Any]]:
    if not 0.0 < near_duplicate_threshold <= 1.0:
        raise ValueError("near_duplicate_threshold must be within (0, 1]")
    golden_texts = [
        (case["case_id"], _normalized_text(case["model_input_text"]))
        for case in controls.cases
    ]
    overlaps: list[dict[str, Any]] = []
    for row in rows:
        text = row.get("model_input_text")
        if not isinstance(text, str) or not text.strip():
            continue
        normalized = _normalized_text(text)
        matches = [
            {
                "case_id": case_id,
                "similarity": round(
                    SequenceMatcher(None, normalized, golden).ratio(), 6
                ),
            }
            for case_id, golden in golden_texts
            if SequenceMatcher(None, normalized, golden).ratio()
            >= near_duplicate_threshold
        ]
        if matches:
            overlaps.append({"sample_id": row.get("sample_id"), "matches": matches})
    return overlaps


def _action_for(
    *, label: str, confidence: float, confidence_tier: str | None
) -> tuple[str, str]:
    tier = confidence_tier or classify_confidence(
        confidence,
        thresholds=ConfidenceThresholds(low=0.50, high=0.80, critical=0.90),
    )
    if label == "Normal":
        return tier, "ALLOWED"
    return tier, {
        "LOW": "ALLOWED",
        "MEDIUM": "THROTTLED",
        "HIGH": "BLOCKED",
        "CRITICAL": "BLOCKED",
    }[tier]


def evaluate_golden_controls(
    controls: GoldenControlSet,
    predictor: Callable[[str], Mapping[str, Any]],
) -> GoldenEvaluation:
    case_results: list[dict[str, Any]] = []
    category_results: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for case in controls.cases:
        prediction = dict(predictor(str(case["model_input_text"])))
        predicted_label = prediction.get("label", prediction.get("prediction"))
        confidence = float(
            prediction.get("confidence", prediction.get("max_prob", 0.0))
        )
        tier, predicted_action = _action_for(
            label=str(predicted_label),
            confidence=confidence,
            confidence_tier=prediction.get("confidence_tier"),
        )
        label_passed = predicted_label == case["expected_label"]
        action_passed = predicted_action == case["expected_action"]
        passed = label_passed and action_passed
        result = {
            "case_id": case["case_id"],
            "category": case["category"],
            "expected_label": case["expected_label"],
            "expected_action": case["expected_action"],
            "predicted_label": predicted_label,
            "predicted_probability": round(confidence, 6),
            "confidence": round(confidence, 6),
            "confidence_tier": tier,
            "predicted_action": predicted_action,
            "label_passed": label_passed,
            "action_passed": action_passed,
            "passed": passed,
        }
        case_results.append(result)
        category = str(case["category"])
        category_results.setdefault(
            category, {"total": 0, "passed_count": 0, "failed_case_ids": []}
        )
        category_results[category]["total"] += 1
        if passed:
            category_results[category]["passed_count"] += 1
        else:
            category_results[category]["failed_case_ids"].append(case["case_id"])
            failures.append(str(case["case_id"]))
    for category_result in category_results.values():
        category_result["passed"] = (
            category_result["passed_count"] == category_result["total"]
        )
    return GoldenEvaluation(
        passed=not failures,
        cases=tuple(case_results),
        category_results=category_results,
        mandatory_failures=failures,
        manifest_sha256=canonical_json_sha256(controls.manifest),
    )
