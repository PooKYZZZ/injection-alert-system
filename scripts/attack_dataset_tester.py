from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_DATASET = REPO_ROOT / "scripts" / "fixtures" / "attack_dataset_samples.json"
DEFAULT_DATASET_CANDIDATES = [
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "test.parquet",
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "validation.parquet",
    REPO_ROOT / "data" / "processed" / "v3_907k_cleaned" / "train.parquet",
    DEFAULT_FIXTURE_DATASET,
]
DEFAULT_ENDPOINT = "http://127.0.0.1:8000/api/predict"
ATTACK_LABELS = {"SQL Injection", "Code Injection", "Other Attacks"}


@dataclass(frozen=True)
class AttackSample:
    row_id: str
    label: str | None
    http_request: str


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
        description="Replay labeled attack samples from a dataset against /api/predict."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Dataset file to use (.parquet, .csv, .json, .jsonl). Defaults to the first existing processed split.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Prediction endpoint. Default: {DEFAULT_ENDPOINT}",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token for protected backend routes. If omitted, reads API_SECRET_KEY from .env.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of samples to send. Default: 50.",
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
        help="Attack labels to include. Default: SQL Injection Code Injection Other Attacks.",
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
        help="Sleep between requests to avoid hammering the app. Default: 0.",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=10,
        help="How many failed/mismatched rows to print in the report. Default: 10.",
    )
    return parser


def load_env_api_key() -> str | None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "API_SECRET_KEY":
            return value.strip().strip('"').strip("'") or None
    return None


def resolve_dataset_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        if not explicit_path.exists():
            if DEFAULT_FIXTURE_DATASET.exists():
                print(
                    f"Warning: dataset not found at {explicit_path}. Falling back to {DEFAULT_FIXTURE_DATASET}.",
                    file=sys.stderr,
                )
                return DEFAULT_FIXTURE_DATASET
            raise FileNotFoundError(f"Dataset not found: {explicit_path}")
        return explicit_path

    for candidate in DEFAULT_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No default dataset split found and no fixture dataset is available. Pass --dataset explicitly."
    )


def load_dataset_rows(dataset_path: Path) -> list[dict[str, Any]]:
    suffix = dataset_path.suffix.lower()

    if suffix == ".parquet":
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Reading .parquet datasets requires pandas with parquet support installed."
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


def extract_label(row: dict[str, Any]) -> str | None:
    for key in ("final_label", "label", "class_label", "prediction", "target"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_http_request(row: dict[str, Any]) -> str:
    combined = row.get("combined_payload") or row.get("http_request")
    if isinstance(combined, str) and combined.strip():
        return combined.strip()

    method = _string(row.get("request_http_method") or row.get("method") or "GET").strip().upper() or "GET"
    path = _string(
        row.get("request_http_request")
        or row.get("request_path")
        or row.get("path")
        or "/"
    ).strip() or "/"
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

        row_id = _string(row.get("payload_hash") or row.get("id") or f"row-{index + 1}")
        samples.append(AttackSample(row_id=row_id, label=label, http_request=http_request))
    return samples


def choose_samples(samples: list[AttackSample], limit: int, seed: int) -> list[AttackSample]:
    if limit <= 0 or len(samples) <= limit:
        return list(samples)
    rng = random.Random(seed)
    return rng.sample(samples, limit)


def send_prediction(
    sample: AttackSample,
    *,
    endpoint: str,
    api_key: str | None,
    timeout: float,
) -> PredictionResult:
    payload = json.dumps({"http_request": sample.http_request}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    started = time.perf_counter()
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
        raw_body = exc.read().decode("utf-8", errors="replace")
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


def print_report(results: list[PredictionResult], show_failures: int) -> None:
    total = len(results)
    succeeded = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]
    labeled = [result for result in succeeded if result.sample.label]
    matched = [
        result
        for result in labeled
        if result.predicted_label == result.sample.label
    ]

    durations = [result.duration_ms for result in results]
    mean_duration = statistics.fmean(durations) if durations else 0.0
    p95_duration = sorted(durations)[max(0, int(len(durations) * 0.95) - 1)] if durations else 0.0

    print(f"Total requests: {total}")
    print(f"Successful responses: {len(succeeded)}")
    print(f"Failed responses: {len(failed)}")
    if labeled:
        print(f"Label matches: {len(matched)}/{len(labeled)} ({(len(matched) / len(labeled)) * 100:.1f}%)")
    print(f"Mean latency: {mean_duration:.1f} ms")
    print(f"p95 latency: {p95_duration:.1f} ms")

    action_counts: dict[str, int] = {}
    for result in succeeded:
        if result.action_taken:
            action_counts[result.action_taken] = action_counts.get(result.action_taken, 0) + 1
    if action_counts:
        print("Actions:")
        for action, count in sorted(action_counts.items()):
            print(f"  {action}: {count}")

    problem_rows = [
        result
        for result in results
        if not result.ok or (result.sample.label and result.predicted_label != result.sample.label)
    ]
    if problem_rows:
        print("\nProblem samples:")
        for result in problem_rows[:show_failures]:
            expected = result.sample.label or "<unlabeled>"
            got = result.predicted_label or result.error or "<no response>"
            print(
                f"  {result.sample.row_id}: expected={expected} got={got} status={result.status_code} latency={result.duration_ms:.1f}ms"
            )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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
            "Warning: no API key configured. Requests will fail if backend auth is enabled.",
            file=sys.stderr,
        )

    print(f"Dataset: {dataset_path}")
    print(f"Selected samples: {len(selected_samples)} of {len(samples)}")
    print(f"Endpoint: {args.endpoint}")

    results: list[PredictionResult] = []
    for index, sample in enumerate(selected_samples, start=1):
        result = send_prediction(
            sample,
            endpoint=args.endpoint,
            api_key=api_key,
            timeout=args.timeout,
        )
        results.append(result)
        status_text = result.status_code if result.status_code is not None else "ERR"
        label_text = result.predicted_label or result.error or "<none>"
        print(
            f"[{index}/{len(selected_samples)}] {sample.row_id} -> {status_text} {label_text} ({result.duration_ms:.1f} ms)"
        )
        if args.pause_ms > 0 and index < len(selected_samples):
            time.sleep(args.pause_ms / 1000.0)

    print()
    print_report(results, args.show_failures)

    return 0 if all(result.ok for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())