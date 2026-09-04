"""Run a bounded, Search Records-only attack test through the local WAF.

The runner sends GET requests only to /records/search?query=... and correlates
each request with the ModSecurity audit log and the backend WAF-ingest lookup.
It is intended to run inside the backend container during the isolated
search-route test Compose overlay.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from uuid import uuid4

from scripts.search_records_attack_catalog import (
    EXPECTED_LABELS,
    FAMILIES,
    ROUTE_PATH,
    load_catalog,
)

DEFAULT_ORIGIN = "http://demo-target-modsecurity:8080"
DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_AUDIT_LOG = "/app/search-test-audit/modsec_audit.jsonl"
MAX_CASES = 150
ALLOWED_ORIGIN_HOSTS = {"demo-target-modsecurity", "127.0.0.1", "localhost", "::1"}
ALLOWED_BACKEND_HOSTS = {"127.0.0.1", "localhost", "::1", "backend"}
REPORT_FIELDS = [
    "run_id",
    "observed_at_utc",
    "environment",
    "origin",
    "route_path",
    "method",
    "catalog_version",
    "case_id",
    "seed_id",
    "family",
    "variant",
    "mutation",
    "description",
    "ground_truth_status",
    "replay_policy",
    "payload",
    "wire_query",
    "payload_sha256",
    "wire_sha256",
    "expected_label",
    "predicted_label",
    "classification_correct",
    "confidence",
    "confidence_level",
    "expected_action",
    "action_taken",
    "action_match",
    "http_status",
    "request_executed",
    "waf_status",
    "waf_rule_ids",
    "waf_score",
    "transaction_id",
    "backend_alert_id",
    "bridge_found",
    "bridge_status",
    "model_version",
    "failure_class",
    "acceptance_status",
    "error",
]
ATTACK_LABELS = set(EXPECTED_LABELS.values())
CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _opener():
    return build_opener(_NoRedirectHandler, ProxyHandler({}))


def _validate_endpoint(value: str, *, allowed_hosts: set[str], label: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or not parsed.hostname
        or parsed.hostname.lower() not in allowed_hosts
    ):
        raise ValueError(
            f"{label} must be a local HTTP origin with no path, query, or credentials"
        )
    if parsed.port is None:
        raise ValueError(f"{label} must include an explicit port")
    return value.rstrip("/")


def _load_cases(
    path: Path, families: list[str] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    catalog = load_catalog(path)
    cases = catalog["cases"]
    selected = (
        [case for case in cases if case["family"] in families]
        if families
        else list(cases)
    )
    if len(selected) > MAX_CASES:
        raise ValueError(f"at most {MAX_CASES} cases may be sent in one run")
    if not selected:
        raise ValueError("catalogue selection is empty")
    return catalog, selected


def _file_offset(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _new_audit_events(path: Path, offset: int) -> tuple[int, list[dict[str, Any]]]:
    try:
        with path.open("rb") as handle:
            if handle.seek(0, 2) < offset:
                offset = 0
            handle.seek(offset)
            content = handle.read()
    except FileNotFoundError:
        return offset, []

    consumed = 0
    events: list[dict[str, Any]] = []
    for line in content.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            break
        consumed += len(line)
        try:
            event = json.loads(line.decode("utf-8"))
        except UnicodeDecodeError, json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return offset + consumed, events


def _request_uri_matches(event: dict[str, Any], case: dict[str, Any]) -> bool:
    transaction = event.get("transaction")
    if not isinstance(transaction, dict):
        return False
    request = transaction.get("request")
    if not isinstance(request, dict):
        return False
    uri = str(request.get("uri") or request.get("path") or "")
    if uri == case["request_uri"]:
        return True
    actual = urlsplit(uri)
    expected = urlsplit(case["request_uri"])
    if actual.path != ROUTE_PATH or expected.path != ROUTE_PATH:
        return False
    return parse_qsl(actual.query, keep_blank_values=True) == parse_qsl(
        expected.query, keep_blank_values=True
    )


def _transaction_metadata(event: dict[str, Any]) -> dict[str, Any]:
    transaction = event.get("transaction")
    if not isinstance(transaction, dict):
        return {}
    request = transaction.get("request")
    request = request if isinstance(request, dict) else {}
    messages = transaction.get("messages")
    messages = messages if isinstance(messages, list) else []
    rule_ids: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        details = message.get("details")
        if isinstance(details, dict) and details.get("ruleId") is not None:
            rule_ids.append(str(details["ruleId"]))
    score = transaction.get("anomaly_score")
    try:
        score = int(score) if score is not None and score != "" else None
    except TypeError, ValueError:
        score = None
    return {
        "transaction_id": str(
            transaction.get("unique_id") or transaction.get("id") or ""
        ),
        "waf_rule_ids": list(dict.fromkeys(rule_ids)),
        "waf_score": score,
        "request_path": str(request.get("uri") or request.get("path") or ""),
    }


def _poll_audit(
    path: Path,
    *,
    offset: int,
    case: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, dict[str, Any] | None]:
    deadline = time.monotonic() + timeout_seconds
    current_offset = offset
    while time.monotonic() < deadline:
        current_offset, events = _new_audit_events(path, current_offset)
        for event in events:
            if _request_uri_matches(event, case):
                return current_offset, event
        time.sleep(0.1)
    return current_offset, None


def _request_status(
    opener, url: str, *, timeout_seconds: float
) -> tuple[int | None, float, str | None]:
    started = time.monotonic()
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "text/html",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-store",
            "User-Agent": "cybertrace-local-search-records-tester/1.0",
        },
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            response.read(1024)
            return int(response.status), (time.monotonic() - started) * 1000, None
    except HTTPError as exc:
        exc.close()
        return int(exc.code), (time.monotonic() - started) * 1000, None
    except (URLError, TimeoutError, OSError) as exc:
        return None, (time.monotonic() - started) * 1000, type(exc).__name__


def _backend_lookup(
    opener,
    backend: str,
    transaction_id: str,
    *,
    api_key: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{backend}/api/internal/waf-events/{transaction_id}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, method="GET", headers=headers)
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(64 * 1024)
            payload = json.loads(body.decode("utf-8"))
            return payload if isinstance(payload, dict) else None, None
    except HTTPError as exc:
        exc.close()
        return None, f"backend_http_{exc.code}"
    except (
        URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        return None, type(exc).__name__


def _poll_backend(
    opener,
    backend: str,
    transaction_id: str,
    *,
    api_key: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any] | None, str | None]:
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        payload, error = _backend_lookup(
            opener,
            backend,
            transaction_id,
            api_key=api_key,
            timeout_seconds=min(5.0, timeout_seconds),
        )
        last_error = error
        if payload and payload.get("found") is True:
            # The ingest endpoint reserves the transaction before running
            # inference.  A lookup can therefore find a durable PROCESSING
            # row before prediction fields are available.  Keep polling until
            # the row reaches a terminal state so the report never records a
            # blank prediction as if it were a completed inference.
            if str(payload.get("status") or "") != "PROCESSING":
                return payload, None
        if error and error.startswith("backend_http_"):
            return None, error
        time.sleep(0.15)
    return None, last_error or "backend_lookup_timeout"


def _expected_action(expected_label: str, confidence_level: str | None) -> str | None:
    if expected_label == "Normal":
        return "ALLOWED"
    if confidence_level == "LOW":
        return "ALLOWED"
    if confidence_level == "MEDIUM":
        return "THROTTLED"
    if confidence_level in {"HIGH", "CRITICAL"}:
        return "BLOCKED"
    return None


def _waf_status(http_status: int | None) -> str:
    if http_status in {403, 406}:
        return "BLOCKED"
    if http_status is not None and 200 <= http_status < 400:
        return "ACCEPTED"
    return "ERROR"


def _acceptance_status(case: dict[str, Any], row: dict[str, Any]) -> str:
    if row["request_executed"] != "True":
        return "EXECUTION_FAILED"
    if row["transaction_id"] == "":
        return "AUDIT_NOT_OBSERVED"
    if row["bridge_found"] != "True":
        return "BRIDGE_NOT_OBSERVED"
    if row["classification_correct"] != "True" or row["action_match"] != "True":
        return "FAIL" if row["is_seed"] == "True" else "REVIEW"
    return "PASS" if row["is_seed"] == "True" else "PASS_CANDIDATE"


def _result_row(
    case: dict[str, Any],
    *,
    run_id: str,
    environment: str,
    origin: str,
    status: int | None,
    duration_ms: float,
    request_error: str | None,
    audit_event: dict[str, Any] | None,
    lookup: dict[str, Any] | None,
    lookup_error: str | None,
    catalog_version: str,
) -> dict[str, Any]:
    audit = _transaction_metadata(audit_event) if audit_event else {}
    transaction_id = str(audit.get("transaction_id") or "")
    predicted = str(lookup.get("prediction") or "") if lookup else ""
    confidence = lookup.get("confidence") if lookup else None
    confidence_level = str(lookup.get("confidence_level") or "") if lookup else ""
    action_taken = str(lookup.get("action_taken") or "") if lookup else ""
    expected_label = case["expected_label"]
    expected_action = _expected_action(expected_label, confidence_level)
    label_match = bool(predicted) and predicted == expected_label
    action_match = bool(action_taken) and expected_action == action_taken
    failure_class = ""
    if request_error:
        failure_class = "REQUEST_FAILED"
    elif not audit_event:
        failure_class = "AUDIT_NOT_OBSERVED"
    elif not lookup:
        failure_class = "BRIDGE_NOT_OBSERVED"
    elif not predicted or confidence is None or not confidence_level:
        failure_class = "INVALID_BACKEND_RESULT"
    row = {
        "run_id": run_id,
        "observed_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "environment": environment,
        "origin": origin,
        "route_path": ROUTE_PATH,
        "method": "GET",
        "catalog_version": catalog_version,
        "case_id": case["case_id"],
        "seed_id": case["seed_id"],
        "family": case["family"],
        "variant": case["variant"],
        "mutation": case["mutation"],
        "description": case["description"],
        "ground_truth_status": case["ground_truth_status"],
        "replay_policy": case["replay_policy"],
        "payload": case["payload"],
        "wire_query": case["wire_query"],
        "payload_sha256": case["payload_sha256"],
        "wire_sha256": case["wire_sha256"],
        "expected_label": expected_label,
        "predicted_label": predicted,
        "classification_correct": str(label_match),
        "confidence": "" if confidence is None else f"{float(confidence):.6f}",
        "confidence_level": confidence_level,
        "expected_action": "" if expected_action is None else expected_action,
        "action_taken": action_taken,
        "action_match": str(action_match),
        "http_status": "" if status is None else str(status),
        "request_executed": str(status is not None),
        "waf_status": _waf_status(status),
        "waf_rule_ids": json.dumps(
            audit.get("waf_rule_ids", []), separators=(",", ":")
        ),
        "waf_score": "" if audit.get("waf_score") is None else str(audit["waf_score"]),
        "transaction_id": transaction_id,
        "backend_alert_id": "" if not lookup else str(lookup.get("alert_id") or ""),
        "bridge_found": str(bool(lookup and lookup.get("found") is True)),
        "bridge_status": "" if not lookup else str(lookup.get("status") or ""),
        "model_version": "" if not lookup else str(lookup.get("model_version") or ""),
        "failure_class": failure_class,
        "acceptance_status": "",
        "error": request_error or lookup_error or "",
        "duration_ms": f"{duration_ms:.2f}",
        "is_seed": str(bool(case.get("is_seed"))),
    }
    row["acceptance_status"] = _acceptance_status(case, row)
    return row


def build_reference_bundle(
    rows: list[dict[str, Any]], *, run_id: str
) -> dict[str, Any]:
    def confirmed(family: str) -> list[dict[str, Any]]:
        return [
            _reference_row(row)
            for row in rows
            if row["family"] == family and row["classification_correct"] == "True"
        ]

    def confidence_cases(level: str) -> list[dict[str, Any]]:
        return [
            _reference_row(row)
            for row in rows
            if row["family"] == "general_attack"
            and row["confidence_level"] == level
            and row["predicted_label"] in ATTACK_LABELS
        ]

    return {
        "schema_version": 1,
        "run_id": run_id,
        "route": {"method": "GET", "path": ROUTE_PATH, "query_parameter": "query"},
        "selection_note": (
            "Exact payloads are preserved for reruns. Confirmed examples have "
            "an exact expected-label match in this run; LOW/MEDIUM general "
            "cases are confidence references and retain their match status."
        ),
        "confirmed_sql_injection_examples": confirmed("sql_injection"),
        "confirmed_code_injection_examples": confirmed("code_injection"),
        "confirmed_general_attack_examples": confirmed("general_attack"),
        "known_low_confidence_general_attack_cases": confidence_cases("LOW"),
        "known_medium_confidence_general_attack_cases": confidence_cases("MEDIUM"),
        "general_low_medium_missed_cases": [
            _reference_row(row)
            for row in rows
            if row["family"] == "general_attack"
            and row["confidence_level"] in {"LOW", "MEDIUM"}
            and row["predicted_label"] == "Normal"
        ],
    }


def _reference_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "case_id",
            "seed_id",
            "family",
            "variant",
            "mutation",
            "payload",
            "wire_query",
            "payload_sha256",
            "wire_sha256",
            "expected_label",
            "predicted_label",
            "classification_correct",
            "confidence",
            "confidence_level",
            "expected_action",
            "action_taken",
            "action_match",
            "http_status",
            "waf_status",
            "transaction_id",
            "backend_alert_id",
            "acceptance_status",
        )
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(
    path: Path, *, metadata: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"metadata": metadata, "rows": rows}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )


def _write_references(path: Path, bundle: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def run(
    *,
    catalog_path: Path,
    origin: str,
    audit_log: Path,
    backend: str,
    api_key: str,
    run_id: str,
    environment: str,
    families: list[str] | None,
    max_rps: float,
    max_runtime_seconds: float,
    request_timeout_seconds: float,
    audit_timeout_seconds: float,
    lookup_timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if max_rps <= 0 or max_rps > 5:
        raise ValueError("max_rps must be greater than zero and no more than 5")
    if max_runtime_seconds <= 0 or max_runtime_seconds > 600:
        raise ValueError("max_runtime_seconds must be between 0 and 600")
    origin = _validate_endpoint(
        origin, allowed_hosts=ALLOWED_ORIGIN_HOSTS, label="origin"
    )
    backend = _validate_endpoint(
        backend, allowed_hosts=ALLOWED_BACKEND_HOSTS, label="backend"
    )
    catalog, cases = _load_cases(catalog_path, families)
    opener = _opener()
    started = time.monotonic()
    next_request_at = started
    rows: list[dict[str, Any]] = []
    consecutive_failures = 0

    for case in cases:
        now = time.monotonic()
        if now - started >= max_runtime_seconds:
            break
        if now < next_request_at:
            time.sleep(next_request_at - now)
        next_request_at = max(next_request_at, time.monotonic()) + (1 / max_rps)
        offset = _file_offset(audit_log)
        status, duration_ms, request_error = _request_status(
            opener,
            f"{origin}{case['request_uri']}",
            timeout_seconds=request_timeout_seconds,
        )
        _, audit_event = _poll_audit(
            audit_log,
            offset=offset,
            case=case,
            timeout_seconds=audit_timeout_seconds,
        )
        audit_meta = _transaction_metadata(audit_event) if audit_event else {}
        lookup = None
        lookup_error = None
        if audit_meta.get("transaction_id"):
            lookup, lookup_error = _poll_backend(
                opener,
                backend,
                audit_meta["transaction_id"],
                api_key=api_key,
                timeout_seconds=lookup_timeout_seconds,
            )
        row = _result_row(
            case,
            run_id=run_id,
            environment=environment,
            origin=origin,
            status=status,
            duration_ms=duration_ms,
            request_error=request_error,
            audit_event=audit_event,
            lookup=lookup,
            lookup_error=lookup_error,
            catalog_version=str(catalog["catalog_version"]),
        )
        rows.append(row)
        if row["failure_class"]:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
        else:
            consecutive_failures = 0

    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "environment": environment,
        "origin": origin,
        "route_path": ROUTE_PATH,
        "method": "GET",
        "catalog_version": catalog["catalog_version"],
        "requested_cases": len(cases),
        "completed_cases": len(rows),
        "max_rps": max_rps,
        "max_runtime_seconds": max_runtime_seconds,
        "attack_requests_only": True,
        "public_endpoint_allowed": False,
    }
    return metadata, rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded attack cases through local Search Records only."
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--audit-log", type=Path, default=Path(DEFAULT_AUDIT_LOG))
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--run-id", default=f"search-records-{uuid4().hex[:12]}")
    parser.add_argument("--environment", default="local-search-records-waf")
    parser.add_argument("--family", choices=FAMILIES, action="append")
    parser.add_argument("--max-rps", type=float, default=3.0)
    parser.add_argument("--max-runtime-seconds", type=float, default=300.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--audit-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--lookup-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--references-output", type=Path)
    return parser


def _summary(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        key = f"{row['family']}:{row['acceptance_status']}"
        counts[key] = counts.get(key, 0) + 1
    return " ".join(
        [
            f"completed={len(rows)}",
            f"predictions={sum(row['bridge_found'] == 'True' for row in rows)}",
            "label_matches="
            f"{sum(row['classification_correct'] == 'True' for row in rows)}",
            f"counts={json.dumps(counts, sort_keys=True, separators=(',', ':'))}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api_key = (
        args.api_key if args.api_key is not None else os.getenv("API_SECRET_KEY", "")
    )
    metadata, rows = run(
        catalog_path=args.catalog,
        origin=args.origin,
        audit_log=args.audit_log,
        backend=args.backend,
        api_key=api_key,
        run_id=args.run_id,
        environment=args.environment,
        families=args.family,
        max_rps=args.max_rps,
        max_runtime_seconds=args.max_runtime_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        audit_timeout_seconds=args.audit_timeout_seconds,
        lookup_timeout_seconds=args.lookup_timeout_seconds,
    )
    if args.output_csv:
        _write_csv(args.output_csv, rows)
    if args.output_json:
        _write_json(args.output_json, metadata=metadata, rows=rows)
    if args.references_output:
        _write_references(
            args.references_output,
            build_reference_bundle(rows, run_id=args.run_id),
        )
    print(_summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
