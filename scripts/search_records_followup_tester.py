"""Run bounded follow-up cases through the local Search Records WAF path.

This runner is intentionally separate from the original three-family runner:
the follow-up catalogue also contains benign ``normal_traffic`` cases and
requires the source-seed field for code-expansion provenance.  It reuses the
existing request, ModSecurity-audit, bridge, and backend-correlation helpers.
No public hostname is accepted and no route other than
``GET /records/search?query=...`` can be loaded from a catalogue.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.search_records_followup_catalog import validate_followup_catalog
from scripts.search_route_attack_tester import (
    ALLOWED_BACKEND_HOSTS,
    ALLOWED_ORIGIN_HOSTS,
    DEFAULT_AUDIT_LOG,
    DEFAULT_BACKEND,
    DEFAULT_ORIGIN,
    ROUTE_PATH,
    _acceptance_status,
    _file_offset,
    _opener,
    _poll_audit,
    _poll_backend,
    _request_status,
    _result_row,
    _validate_endpoint,
)

MAX_CASES = 200
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
    "source_seed_payload",
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
    "expected_waf",
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


def _load_cases(
    path: Path, requested_family: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    catalog = validate_followup_catalog(path)
    cases = list(catalog["cases"])
    if requested_family:
        cases = [case for case in cases if case["family"] == requested_family]
    if not cases:
        raise ValueError("follow-up catalogue selection is empty")
    if len(cases) > MAX_CASES:
        raise ValueError(f"at most {MAX_CASES} cases may be sent in one run")
    return catalog, cases


def _row_with_provenance(
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
        catalog_version=catalog_version,
    )
    row["source_seed_payload"] = str(
        case.get("source_seed_payload") or case["payload"]
    )
    row["expected_waf"] = str(case.get("expected_waf") or "")
    row["acceptance_status"] = _acceptance_status(case, row)
    return row


def run(
    *,
    catalog_path: Path,
    origin: str,
    audit_log: Path,
    backend: str,
    api_key: str,
    run_id: str,
    environment: str,
    family: str | None,
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
    catalog, cases = _load_cases(catalog_path, family)
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
        audit_meta = (
            _transaction_metadata_for_runner(audit_event) if audit_event else {}
        )
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
        row = _row_with_provenance(
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
        "family": family or "catalog-defined",
        "requested_cases": len(cases),
        "completed_cases": len(rows),
        "max_rps": max_rps,
        "max_runtime_seconds": max_runtime_seconds,
        "search_records_only": True,
        "public_endpoint_allowed": False,
        "classification_failures_do_not_stop_run": True,
    }
    return metadata, rows


def _transaction_metadata_for_runner(
    event: dict[str, Any] | None,
) -> dict[str, Any]:
    """Keep the runner's dependency on the existing private helper explicit."""
    from scripts.search_route_attack_tester import _transaction_metadata

    return _transaction_metadata(event) if event else {}


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


def _summary(rows: list[dict[str, Any]]) -> str:
    label_counts: dict[str, int] = {}
    for row in rows:
        label = row["predicted_label"] or "<missing>"
        label_counts[label] = label_counts.get(label, 0) + 1
    return " ".join(
        [
            f"completed={len(rows)}",
            f"correlated={sum(row['bridge_found'] == 'True' for row in rows)}",
            "label_matches="
            f"{sum(row['classification_correct'] == 'True' for row in rows)}",
            "predicted="
            f"{json.dumps(label_counts, sort_keys=True, separators=(',', ':'))}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded follow-up cases through local Search Records only."
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--audit-log", type=Path, default=Path(DEFAULT_AUDIT_LOG))
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--api-key", default=None)
    parser.add_argument(
        "--run-id", default=f"search-records-followup-{uuid4().hex[:12]}"
    )
    parser.add_argument("--environment", default="local-search-records-waf-followup")
    parser.add_argument("--family", choices=("code_injection", "normal_traffic"))
    parser.add_argument("--max-rps", type=float, default=3.0)
    parser.add_argument("--max-runtime-seconds", type=float, default=300.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--audit-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--lookup-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--output-json", type=Path)
    return parser


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
        family=args.family,
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
    print(_summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
