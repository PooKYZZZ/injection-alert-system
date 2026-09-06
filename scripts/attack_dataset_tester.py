from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from web_app.domain.classification_scope import is_actionable_attack_class

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_DATASET = (
    REPO_ROOT / "scripts" / "fixtures" / "attack_dataset_samples.json"
)
DEFAULT_DATASET_CANDIDATES = [
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "test.parquet",
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "validation.parquet",
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "train.parquet",
    DEFAULT_FIXTURE_DATASET,
]
DEFAULT_ENDPOINT = "http://127.0.0.1:8000/api/predict"
ATTACK_LABELS = {"SQL Injection", "Code Injection", "Other Attacks"}
KNOWN_LABELS = ATTACK_LABELS | {"Normal"}
LOCAL_ENDPOINT_HOSTS = {"127.0.0.1", "localhost", "::1", "backend"}
MAX_BATCH_REQUESTS = 100
TRANSIENT_HTTP_STATUSES = {408, 425, 429}
REPORT_FIELDS = [
    "run_id",
    "observed_at_utc",
    "environment",
    "endpoint",
    "catalog_version",
    "case_id",
    "case_version",
    "source_fixture_id",
    "family",
    "variant",
    "description",
    "selection_tags",
    "ground_truth_status",
    "replay_policy",
    "input_sha256",
    "expected_label",
    "predicted_label",
    "label_match",
    "expected_action",
    "action_taken",
    "action_match",
    "confidence",
    "confidence_tier",
    "model_version",
    "model_digest",
    "checkpoint_digest",
    "preprocessing_version",
    "model_temperature",
    "threshold_low",
    "threshold_high",
    "threshold_critical",
    "status_code",
    "http_ok",
    "duration_ms",
    "expected_waf",
    "waf_status",
    "waf_rule_ids",
    "waf_score",
    "transaction_id",
    "backend_alert_id",
    "failure_class",
    "acceptance_status",
    "error",
]


@dataclass(frozen=True)
class AttackSample:
    row_id: str
    label: str | None
    http_request: str
    case_id: str = ""
    case_version: int = 1
    source_fixture_id: str = ""
    family: str = "unknown"
    variant: str = "identity"
    description: str = ""
    ground_truth_status: str = "unknown"
    expected_waf: str = "NOT_SPECIFIED"
    replay_policy: str = "not_specified"
    selection_tags: tuple[str, ...] = ()
    catalog_version: str = ""


@dataclass(frozen=True)
class PredictionResult:
    sample: AttackSample
    ok: bool
    status_code: int | None
    duration_ms: float
    predicted_label: str | None
    confidence: float | None
    confidence_level: str | None
    action_taken: str | None
    error: str | None
    raw_body: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded, local-first prediction batch and optionally write "
            "secret-safe evidence reports."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help=(
            "Dataset file to use (.parquet, .csv, .json, .jsonl). Defaults "
            "to the first existing processed split."
        ),
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Prediction endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--allow-nonlocal-endpoint",
        action="store_true",
        help=(
            "Explicitly allow a non-local endpoint; public testing is not recommended."
        ),
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token. If omitted, reads API_SECRET_KEY from the ignored .env.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help=(
            f"Maximum samples in this batch, capped at {MAX_BATCH_REQUESTS}. "
            "Default: 50."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used when sampling rows. Default: 42.",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        default=sorted(ATTACK_LABELS),
        help="Attack labels to include. Default: all attack labels.",
    )
    parser.add_argument(
        "--include-normal",
        action="store_true",
        help="Include rows labeled Normal when the dataset contains labels.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds. Default: 15.",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=0,
        help="Additional pause between requests. Default: 0.",
    )
    parser.add_argument(
        "--max-rps",
        type=float,
        default=5.0,
        help="Maximum request rate enforced between requests. Default: 5.",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=120.0,
        help="Maximum runtime for the batch. Default: 120 seconds.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Retries for transient failures only. Default: 1.",
    )
    parser.add_argument(
        "--backoff-ms",
        type=int,
        default=250,
        help="Initial exponential backoff for transient retries. Default: 250.",
    )
    parser.add_argument(
        "--circuit-breaker-failures",
        type=int,
        default=3,
        help="Stop after this many consecutive transient failures. Default: 3.",
    )
    parser.add_argument(
        "--stop-file",
        type=Path,
        help="Stop before the next request when this local file exists.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Evidence run ID. Generated when omitted.",
    )
    parser.add_argument(
        "--environment",
        default="local-offline",
        help="Environment label written to reports. Default: local-offline.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        help="Optional secret-safe CSV evidence path.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        help="Optional secret-safe JSONL evidence path.",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=10,
        help="How many failed/mismatched rows to print. Default: 10.",
    )
    return parser


def load_env_value(name: str) -> str | None:
    """Read one requested dotenv value without printing or exposing it."""

    environment_value = os.environ.get(name)
    if environment_value is not None:
        return environment_value.strip().strip('"').strip("'") or None

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


def load_env_api_key() -> str | None:
    return load_env_value("API_SECRET_KEY")


def resolve_dataset_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        if not explicit_path.exists():
            if DEFAULT_FIXTURE_DATASET.exists():
                print(
                    f"Warning: dataset not found at {explicit_path}. "
                    f"Falling back to {DEFAULT_FIXTURE_DATASET}.",
                    file=sys.stderr,
                )
                return DEFAULT_FIXTURE_DATASET
            raise FileNotFoundError(f"Dataset not found: {explicit_path}")
        return explicit_path

    for candidate in DEFAULT_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No default dataset split found and no fixture dataset is available. "
        "Pass --dataset explicitly."
    )


def load_dataset_rows(dataset_path: Path) -> list[dict[str, Any]]:
    suffix = dataset_path.suffix.lower()

    if suffix == ".parquet":
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Reading .parquet datasets requires pandas with parquet support "
                "installed."
            ) from exc
        return pd.read_parquet(dataset_path).to_dict(orient="records")

    if suffix == ".csv":
        with dataset_path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    if suffix == ".json":
        with dataset_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array in {dataset_path}")
        return [row for row in payload if isinstance(row, dict)]

    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with dataset_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    rows.append(parsed)
        return rows

    raise ValueError(f"Unsupported dataset format: {dataset_path.suffix}")


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _integer(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
    except TypeError, ValueError:
        return default
    return parsed if parsed >= 1 else default


def _tags(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return (value,) if value else ()
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def extract_label(row: dict[str, Any]) -> str | None:
    for key in (
        "expected_label",
        "final_label",
        "label",
        "class_label",
        "prediction",
        "target",
    ):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def infer_family(label: str | None) -> str:
    return {
        "Normal": "normal",
        "SQL Injection": "sql_injection",
        "Code Injection": "code_injection",
        "Other Attacks": "other_attacks",
    }.get(label or "", "unknown")


def build_http_request(row: dict[str, Any]) -> str:
    combined = row.get("http_request") or row.get("combined_payload")
    if isinstance(combined, str) and combined.strip():
        return combined.strip()

    method = (
        _string(row.get("request_http_method") or row.get("method") or "GET")
        .strip()
        .upper()
        or "GET"
    )
    path = (
        _string(
            row.get("request_http_request")
            or row.get("request_path")
            or row.get("path")
            or "/"
        ).strip()
        or "/"
    )
    if not path.startswith("/"):
        path = f"/{path}"

    body = _string(row.get("request_body") or row.get("body")).strip()
    lines = [f"{method} {path} HTTP/1.1", "Host: localhost"]
    if body:
        lines.append(f"Content-Length: {len(body.encode('utf-8'))}")
        lines.append("")
        lines.append(body)
    return "\n".join(lines)


def normalize_samples(
    rows: list[dict[str, Any]],
    *,
    include_labels: set[str],
    include_normal: bool,
) -> list[AttackSample]:
    samples: list[AttackSample] = []
    for index, row in enumerate(rows):
        label = extract_label(row)
        if label is not None:
            if label == "Normal" and not include_normal:
                continue
            if label != "Normal" and include_labels and label not in include_labels:
                continue

        http_request = build_http_request(row)
        if not http_request.strip():
            continue

        row_id = _string(
            row.get("case_id")
            or row.get("payload_hash")
            or row.get("id")
            or f"row-{index + 1}"
        )
        samples.append(
            AttackSample(
                row_id=row_id,
                label=label,
                http_request=http_request,
                case_id=_string(row.get("case_id") or row_id),
                case_version=_integer(row.get("case_version")),
                source_fixture_id=_string(
                    row.get("source_fixture_id") or row.get("id")
                ),
                family=_string(row.get("family") or infer_family(label)) or "unknown",
                variant=_string(row.get("variant")) or "identity",
                description=_string(row.get("description")),
                ground_truth_status=_string(row.get("ground_truth_status"))
                or ("provided" if label else "unknown"),
                expected_waf=_string(row.get("expected_waf")) or "NOT_SPECIFIED",
                replay_policy=_string(row.get("replay_policy")) or "not_specified",
                selection_tags=_tags(row.get("selection_tags")),
                catalog_version=_string(row.get("catalog_version")),
            )
        )
    return samples


def choose_samples(
    samples: list[AttackSample], limit: int, seed: int
) -> list[AttackSample]:
    effective_limit = (
        MAX_BATCH_REQUESTS if limit <= 0 else min(limit, MAX_BATCH_REQUESTS)
    )
    if len(samples) <= effective_limit:
        return list(samples)
    rng = random.Random(seed)
    return rng.sample(samples, effective_limit)


def _is_transient(status_code: int | None) -> bool:
    return (
        status_code is None
        or status_code in TRANSIENT_HTTP_STATUSES
        or status_code >= 500
    )


def send_prediction(
    sample: AttackSample,
    *,
    endpoint: str,
    api_key: str | None,
    timeout: float,
    max_retries: int = 0,
    backoff_seconds: float = 0.25,
) -> PredictionResult:
    payload = json.dumps({"http_request": sample.http_request}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        endpoint, data=payload, headers=headers, method="POST"
    )
    started = time.perf_counter()
    attempts = max(0, max_retries) + 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
                duration_ms = (time.perf_counter() - started) * 1000.0
                parsed = json.loads(raw_body)
                return PredictionResult(
                    sample=sample,
                    ok=True,
                    status_code=response.status,
                    duration_ms=duration_ms,
                    predicted_label=parsed.get("class_label"),
                    confidence=parsed.get("confidence"),
                    confidence_level=parsed.get("confidence_level"),
                    action_taken=parsed.get("action_taken"),
                    error=None,
                    raw_body=raw_body,
                )
        except urllib.error.HTTPError as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            try:
                raw_body = exc.read().decode("utf-8", errors="replace")
            except OSError:
                raw_body = None
            if _is_transient(exc.code) and attempt + 1 < attempts:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            return PredictionResult(
                sample=sample,
                ok=False,
                status_code=exc.code,
                duration_ms=duration_ms,
                predicted_label=None,
                confidence=None,
                confidence_level=None,
                action_taken=None,
                error=f"HTTP {exc.code}",
                raw_body=raw_body,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt + 1 < attempts:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            duration_ms = (time.perf_counter() - started) * 1000.0
            return PredictionResult(
                sample=sample,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                predicted_label=None,
                confidence=None,
                confidence_level=None,
                action_taken=None,
                error=str(exc),
                raw_body=None,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            return PredictionResult(
                sample=sample,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                predicted_label=None,
                confidence=None,
                confidence_level=None,
                action_taken=None,
                error=str(exc),
                raw_body=None,
            )

    raise AssertionError("prediction retry loop returned without a result")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeError, json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_model_directory() -> Path | None:
    configured = load_env_value("MODEL_REGISTRY_PATH")
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    if (candidate / "serving_manifest.json").is_file() or (
        candidate / "config_used.json"
    ).is_file():
        return candidate

    staging = candidate / "staging" if (candidate / "staging").is_dir() else candidate
    pointer = staging / "active_model.json"
    if pointer.is_file():
        payload = _read_json_object(pointer)
        directory = payload.get("directory")
        if isinstance(directory, str) and Path(directory).name == directory:
            pointed = staging / directory
            if pointed.is_dir():
                return pointed

    candidates = (
        sorted(
            [
                path
                for path in staging.iterdir()
                if path.is_dir() and path.name.startswith("distilbert_")
            ],
            key=lambda path: path.name,
            reverse=True,
        )
        if staging.is_dir()
        else []
    )
    return candidates[0] if candidates else None


def collect_local_model_metadata() -> dict[str, Any]:
    """Collect non-secret model identity from the configured local artifact."""

    metadata: dict[str, Any] = {
        "model_version": "",
        "model_digest": "",
        "checkpoint_digest": "",
        "preprocessing_version": "",
        "model_temperature": "",
        "threshold_low": load_env_value("CONFIDENCE_LOW_THRESHOLD") or "0.50",
        "threshold_high": load_env_value("CONFIDENCE_HIGH_THRESHOLD") or "0.80",
        "threshold_critical": load_env_value("CONFIDENCE_CRITICAL_THRESHOLD") or "0.90",
    }
    model_dir = _resolve_model_directory()
    if model_dir is None:
        return metadata

    manifest = _read_json_object(model_dir / "serving_manifest.json")
    config = _read_json_object(model_dir / "config_used.json")
    summary = _read_json_object(model_dir / "summary_metrics.json")
    metadata["model_version"] = (
        manifest.get("model_version") or config.get("model_version") or model_dir.name
    )
    metadata["checkpoint_digest"] = (
        manifest.get("checkpoint_sha256") or config.get("checkpoint_sha256") or ""
    )
    metadata["preprocessing_version"] = (
        config.get("preprocessing_version")
        or manifest.get("preprocessing_version")
        or summary.get("preprocessing_version")
        or ""
    )
    metadata["model_temperature"] = manifest.get("temperature") or ""
    metadata["artifact_manifest_digest"] = summary.get("artifact_manifest_sha256") or ""
    try:
        from ml_model.retraining.content_digest import compute_content_digest

        metadata["model_digest"] = compute_content_digest(model_dir)
    except ImportError, OSError, ValueError:
        metadata["model_digest"] = metadata["artifact_manifest_digest"]
    return metadata


def validate_endpoint(endpoint: str, *, allow_nonlocal: bool) -> None:
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("endpoint must be an HTTP or HTTPS URL with a hostname")
    if parsed.hostname.lower() not in LOCAL_ENDPOINT_HOSTS and not allow_nonlocal:
        raise ValueError(
            "refusing non-local endpoint; use the local backend or explicitly "
            "pass --allow-nonlocal-endpoint"
        )


def expected_action_for(
    expected_label: str | None, confidence_level: str | None
) -> str | None:
    if expected_label == "Normal":
        return "ALLOWED"
    if not is_actionable_attack_class(expected_label):
        return None
    return {
        "LOW": "ALLOWED",
        "MEDIUM": "THROTTLED",
        "HIGH": "BLOCKED",
        "CRITICAL": "BLOCKED",
    }.get(confidence_level or "")


def classify_failure(result: PredictionResult) -> str:
    if not result.ok:
        return "infrastructure"
    if result.sample.label and result.predicted_label != result.sample.label:
        return "ml_label"
    if (
        result.predicted_label is None
        or result.confidence is None
        or result.confidence_level is None
    ):
        return "confidence/calibration"
    expected_action = expected_action_for(result.sample.label, result.confidence_level)
    if expected_action is None:
        return "policy" if result.action_taken is not None else ""
    if result.action_taken is None:
        return "confidence/calibration"
    if result.action_taken != expected_action:
        return "policy"
    return ""


def acceptance_status(result: PredictionResult) -> str:
    if not result.ok:
        return "FAIL"
    expected_label = result.sample.label
    if (
        expected_label is None
        or result.predicted_label is None
        or result.confidence is None
        or result.confidence_level is None
    ):
        return "REVIEW"
    expected_action = expected_action_for(expected_label, result.confidence_level)
    label_ok = result.predicted_label == expected_label
    action_ok = result.action_taken == expected_action
    if expected_action is not None and result.action_taken is None:
        return "REVIEW"
    if not label_ok or not action_ok:
        return (
            "FAIL"
            if result.sample.ground_truth_status in {"approved_fixture", "verified"}
            else "REVIEW"
        )
    return (
        "PASS"
        if result.sample.ground_truth_status in {"approved_fixture", "verified"}
        else "REVIEW"
    )


def _report_row(
    result: PredictionResult,
    *,
    run_id: str,
    observed_at_utc: str,
    environment: str,
    endpoint: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    expected_label = result.sample.label or ""
    label_match = (
        ""
        if not expected_label or not result.predicted_label
        else str(result.predicted_label == expected_label)
    )
    expected_action = expected_action_for(result.sample.label, result.confidence_level)
    action_match = (
        ""
        if not result.sample.label
        else str(result.action_taken == expected_action)
    )
    input_sha256 = hashlib.sha256(
        result.sample.http_request.encode("utf-8")
    ).hexdigest()
    return {
        "run_id": run_id,
        "observed_at_utc": observed_at_utc,
        "environment": environment,
        "endpoint": endpoint,
        "catalog_version": result.sample.catalog_version,
        "case_id": result.sample.case_id,
        "case_version": result.sample.case_version,
        "source_fixture_id": result.sample.source_fixture_id,
        "family": result.sample.family,
        "variant": result.sample.variant,
        "description": result.sample.description,
        "selection_tags": json.dumps(result.sample.selection_tags),
        "ground_truth_status": result.sample.ground_truth_status,
        "replay_policy": result.sample.replay_policy,
        "input_sha256": input_sha256,
        "expected_label": expected_label,
        "predicted_label": result.predicted_label or "",
        "label_match": label_match,
        "expected_action": expected_action or "",
        "action_taken": result.action_taken or "",
        "action_match": action_match,
        "confidence": result.confidence if result.confidence is not None else "",
        "confidence_tier": result.confidence_level or "",
        "model_version": metadata.get("model_version", ""),
        "model_digest": metadata.get("model_digest", ""),
        "checkpoint_digest": metadata.get("checkpoint_digest", ""),
        "preprocessing_version": metadata.get("preprocessing_version", ""),
        "model_temperature": metadata.get("model_temperature", ""),
        "threshold_low": metadata.get("threshold_low", ""),
        "threshold_high": metadata.get("threshold_high", ""),
        "threshold_critical": metadata.get("threshold_critical", ""),
        "status_code": result.status_code if result.status_code is not None else "",
        "http_ok": str(result.ok),
        "duration_ms": round(result.duration_ms, 3),
        "expected_waf": result.sample.expected_waf,
        "waf_status": "NOT_COLLECTED",
        "waf_rule_ids": "",
        "waf_score": "",
        "transaction_id": "",
        "backend_alert_id": "",
        "failure_class": classify_failure(result),
        "acceptance_status": acceptance_status(result),
        "error": result.error or "",
    }


def write_evidence_csv(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_evidence_jsonl(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def print_report(results: list[PredictionResult], show_failures: int) -> None:
    total = len(results)
    succeeded = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]
    labeled = [result for result in succeeded if result.sample.label]
    matched = [
        result for result in labeled if result.predicted_label == result.sample.label
    ]

    durations = [result.duration_ms for result in results]
    mean_duration = statistics.fmean(durations) if durations else 0.0
    p95_duration = (
        sorted(durations)[max(0, int(len(durations) * 0.95) - 1)] if durations else 0.0
    )

    print(f"Total requests: {total}")
    print(f"Successful responses: {len(succeeded)}")
    print(f"Failed responses: {len(failed)}")
    if labeled:
        print(
            f"Label matches: {len(matched)}/{len(labeled)} "
            f"({(len(matched) / len(labeled)) * 100:.1f}%)"
        )
    print(f"Mean latency: {mean_duration:.1f} ms")
    print(f"p95 latency: {p95_duration:.1f} ms")

    tier_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for result in succeeded:
        if result.confidence_level:
            tier_counts[result.confidence_level] = (
                tier_counts.get(result.confidence_level, 0) + 1
            )
        if result.action_taken:
            action_counts[result.action_taken] = (
                action_counts.get(result.action_taken, 0) + 1
            )
    if tier_counts:
        print("Confidence tiers:")
        for tier, count in sorted(tier_counts.items()):
            print(f"  {tier}: {count}")
    if action_counts:
        print("Actions:")
        for action, count in sorted(action_counts.items()):
            print(f"  {action}: {count}")

    problem_rows = [
        result
        for result in results
        if not result.ok
        or (result.sample.label and result.predicted_label != result.sample.label)
    ]
    if problem_rows:
        print("\nProblem samples:")
        for result in problem_rows[:show_failures]:
            expected = result.sample.label or "<unlabeled>"
            got = result.predicted_label or result.error or "<no response>"
            print(
                f"  {result.sample.case_id}: expected={expected} got={got} "
                f"status={result.status_code} latency={result.duration_ms:.1f}ms"
            )


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.limit < 0 or args.limit > MAX_BATCH_REQUESTS:
        parser.error(f"--limit must be between 0 and {MAX_BATCH_REQUESTS}")
    if args.timeout <= 0 or args.max_runtime_seconds <= 0 or args.max_rps <= 0:
        parser.error("timeout, max-runtime-seconds, and max-rps must be positive")
    if args.pause_ms < 0 or args.max_retries < 0 or args.backoff_ms < 0:
        parser.error("pause-ms, max-retries, and backoff-ms cannot be negative")
    if args.circuit_breaker_failures < 1:
        parser.error("circuit-breaker-failures must be at least 1")
    validate_endpoint(args.endpoint, allow_nonlocal=args.allow_nonlocal_endpoint)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _validate_args(parser, args)

    try:
        dataset_path = resolve_dataset_path(args.dataset)
        rows = load_dataset_rows(dataset_path)
        samples = normalize_samples(
            rows,
            include_labels=set(args.labels),
            include_normal=args.include_normal,
        )
    except Exception as exc:
        print(f"Failed to prepare dataset: {exc}", file=sys.stderr)
        return 1

    if not samples:
        print("No usable samples found after filtering.", file=sys.stderr)
        return 1

    selected_samples = choose_samples(samples, args.limit, args.seed)
    api_key = args.api_key if args.api_key is not None else load_env_api_key()
    if not api_key:
        print(
            "Warning: no API key configured. Requests will fail if backend auth "
            "is enabled.",
            file=sys.stderr,
        )

    run_id = args.run_id or (
        f"attack-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    )
    metadata = collect_local_model_metadata()
    print(f"Dataset: {dataset_path}")
    print(f"Selected samples: {len(selected_samples)} of {len(samples)}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Run ID: {run_id}")

    results: list[PredictionResult] = []
    failure_streak = 0
    stop_reason = "completed"
    started = time.monotonic()
    min_interval_seconds = 1.0 / args.max_rps

    try:
        for index, sample in enumerate(selected_samples, start=1):
            if args.stop_file and args.stop_file.exists():
                stop_reason = "manual_stop_file"
                break
            if time.monotonic() - started >= args.max_runtime_seconds:
                stop_reason = "max_runtime"
                break

            result = send_prediction(
                sample,
                endpoint=args.endpoint,
                api_key=api_key,
                timeout=args.timeout,
                max_retries=args.max_retries,
                backoff_seconds=args.backoff_ms / 1000.0,
            )
            results.append(result)
            status_text = (
                result.status_code if result.status_code is not None else "ERR"
            )
            label_text = result.predicted_label or result.error or "<none>"
            print(
                f"[{index}/{len(selected_samples)}] {sample.case_id} -> "
                f"{status_text} {label_text} ({result.duration_ms:.1f} ms)"
            )

            if result.ok:
                failure_streak = 0
            elif _is_transient(result.status_code):
                failure_streak += 1
                if failure_streak >= args.circuit_breaker_failures:
                    stop_reason = "circuit_breaker"
                    break

            if index < len(selected_samples):
                time.sleep(max(args.pause_ms / 1000.0, min_interval_seconds))
    except KeyboardInterrupt:
        stop_reason = "manual_interrupt"

    print(f"Stop reason: {stop_reason}")
    print()
    print_report(results, args.show_failures)

    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report_rows = [
        _report_row(
            result,
            run_id=run_id,
            observed_at_utc=observed_at,
            environment=args.environment,
            endpoint=args.endpoint,
            metadata=metadata,
        )
        for result in results
    ]
    try:
        if args.output_csv:
            write_evidence_csv(report_rows, args.output_csv)
            print(f"CSV evidence: {args.output_csv}")
        if args.output_jsonl:
            write_evidence_jsonl(report_rows, args.output_jsonl)
            print(f"JSONL evidence: {args.output_jsonl}")
    except OSError as exc:
        print(f"Failed to write evidence report: {exc}", file=sys.stderr)
        return 1

    if stop_reason != "completed" or not results:
        return 2
    return 0 if all(result.ok for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
