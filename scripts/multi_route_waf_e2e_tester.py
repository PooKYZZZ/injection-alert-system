"""Run a bounded, route-aware WAF-ML test against an isolated local portal.

The runner visits every protected page, submits valid normal forms, and sends
one SQLi and one code-injection probe through each applicable user-controlled
field. It never follows attack redirects and never records submitted values in
its report. Run it inside the test Compose network so neither endpoint can be
redirected to a public host.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from uuid import uuid4

from scripts.search_records_attack_catalog import load_catalog

DEFAULT_ORIGIN = "http://demo-target-modsecurity:8080"
DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_AUDIT_LOG = "/app/m08-e2e-audit/modsec_audit.jsonl"
DEFAULT_OUTPUT_DIR = "/app/m08-e2e-results"
ALLOWED_ORIGIN_HOSTS = {"demo-target-modsecurity", "127.0.0.1", "localhost", "::1"}
ALLOWED_BACKEND_HOSTS = {"127.0.0.1", "localhost", "::1", "backend"}
REDIRECT_CODES = {301, 302, 303, 307, 308}
ATTACK_LABELS = {"sql_injection": "SQL Injection", "code_injection": "Code Injection"}
REPORT_FIELDS = [
    "run_id",
    "test_id",
    "route",
    "method",
    "scenario",
    "catalog_case_id",
    "http_status",
    "follow_status",
    "operation_completed",
    "response_marker_match",
    "transaction_id",
    "ingest_source",
    "source_provenance",
    "source_verification_status",
    "bridge_found",
    "bridge_status",
    "prediction",
    "model_version",
    "confidence",
    "confidence_level",
    "ml_action_recommendation",
    "recorded_policy_decision",
    "recorded_policy_decision_reason",
    "observed_http_effect",
    "crs_score",
    "crs_rule_ids",
    "expected_prediction",
    "classification_match",
    "alert_id",
    "alert_visible_in_api",
    "request_error",
]


@dataclass(frozen=True)
class RouteSpec:
    route: str
    method: str
    path: str
    normal_query: dict[str, str] | None = None
    normal_form: dict[str, str] | None = None
    attack_field: str | None = None
    attack_location: str | None = None
    attack_enabled: bool = False
    follows_success_redirect: bool = False
    normal_response_marker: str | None = None


@dataclass(frozen=True)
class Scenario:
    route: RouteSpec
    scenario: str
    test_id: str
    query: dict[str, str]
    form: dict[str, str] | None
    expected_prediction: str | None = None
    catalog_case_id: str | None = None


ROUTES = (
    RouteSpec("search_records", "GET", "/records/search", {"query": "LND-2026-0001"}, attack_field="query", attack_location="query", attack_enabled=True, normal_response_marker="LND-2026-0001"),
    RouteSpec("track_status", "GET", "/transactions/status", {"ref": "TXN-100201"}, attack_field="ref", attack_location="query", attack_enabled=True, normal_response_marker="TXN-100201"),
    RouteSpec("record_detail", "GET", "/records/LND-2026-0001", attack_field="probe", attack_location="query", attack_enabled=True, normal_response_marker="LND-2026-0001"),
    RouteSpec("request_copy_page", "GET", "/records/LND-2026-0001/request-copy", attack_field="probe", attack_location="query", attack_enabled=True, normal_response_marker="LND-2026-0001"),
    RouteSpec("support_page", "GET", "/support"),
    RouteSpec("appointment_page", "GET", "/appointments"),
    RouteSpec("demo_login_page", "GET", "/login"),
    RouteSpec("comments_page", "GET", "/comments"),
    RouteSpec(
        "book_appointment",
        "POST",
        "/appointments/submit",
        normal_form={
            "fullName": "CyberTrace QA",
            "email": "cybertrace@example.invalid",
            "branch": "Pasig Branch Office",
            "serviceType": "Boundary Dispute Arbitration",
            "preferredDate": (date.today() + timedelta(days=30)).isoformat(),
            "notes": "",
        },
        attack_field="notes",
        attack_location="form",
        attack_enabled=True,
        follows_success_redirect=True,
        normal_response_marker="Appointment request received",
    ),
    RouteSpec(
        "support_desk",
        "POST",
        "/support/submit",
        normal_form={
            "subject": "Parcel map guidance",
            "category": "Cadastral Index Mapping",
            "email": "cybertrace@example.invalid",
            "message": "Please tell me which index map covers the sample property.",
        },
        attack_field="message",
        attack_location="form",
        attack_enabled=True,
        follows_success_redirect=True,
        normal_response_marker="Support ticket submitted",
    ),
    RouteSpec(
        "demo_login_submit",
        "POST",
        "/login/submit",
        normal_form={
            "username": "cybertrace-qa-user",
            "password": "synthetic-password-never-forwarded",
        },
        attack_field="username",
        attack_location="form",
        attack_enabled=True,
        follows_success_redirect=True,
        normal_response_marker="Demo login received",
    ),
    RouteSpec(
        "request_copy_submit",
        "POST",
        "/records/LND-2026-0001/request-copy/submit",
        normal_form={
            "fullName": "CyberTrace QA",
            "email": "cybertrace@example.invalid",
            "purpose": "Personal Ownership Verification",
            "deliveryOption": "Digital copy",
            "remarks": "",
        },
        attack_field="remarks",
        attack_location="form",
        attack_enabled=True,
        follows_success_redirect=True,
        normal_response_marker="Copy Request for Deed",
    ),
    RouteSpec(
        "comments_submit",
        "POST",
        "/comments/submit",
        normal_form={
            "displayName": "CyberTrace QA",
            "message": "The sample registry result was clear and easy to review.",
        },
        attack_field="message",
        attack_location="form",
        attack_enabled=True,
        follows_success_redirect=True,
        normal_response_marker="Comment Published Successfully!",
    ),
)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _opener():
    return build_opener(_NoRedirectHandler, ProxyHandler({}))


def validate_origin(value: str, *, allowed_hosts: set[str], label: str) -> str:
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
        or parsed.port is None
    ):
        raise ValueError(f"{label} must be an explicit-port local HTTP origin")
    return value.rstrip("/")


def build_scenarios(
    catalog: dict[str, Any], *, run_id: str, include_normal: bool = True
) -> list[Scenario]:
    seed_cases: dict[str, list[dict[str, Any]]] = {}
    for family in ATTACK_LABELS:
        seed_cases[family] = [
            case
            for case in catalog.get("cases", [])
            if case.get("family") == family and case.get("is_seed") is True
        ]
        if not seed_cases[family]:
            raise ValueError(f"catalog has no seed cases for {family}")

    scenarios: list[Scenario] = []
    serial = 0
    if include_normal:
        for route in ROUTES:
            serial += 1
            form = dict(route.normal_form) if route.normal_form is not None else None
            scenarios.append(
                Scenario(
                    route=route,
                    scenario="normal",
                    test_id=f"m08-{run_id[:8]}-{serial}-{uuid4().hex[:8]}",
                    query=dict(route.normal_query or {}),
                    form=form,
                    expected_prediction="Normal",
                )
            )

    family_offsets = {family: 0 for family in ATTACK_LABELS}
    for route in ROUTES:
        if not route.attack_enabled or not route.attack_field:
            continue
        for family, expected in ATTACK_LABELS.items():
            cases = seed_cases[family]
            case = cases[family_offsets[family] % len(cases)]
            family_offsets[family] += 1
            serial += 1
            query = dict(route.normal_query or {})
            form = dict(route.normal_form) if route.normal_form is not None else None
            if route.attack_location == "query":
                query[route.attack_field] = str(case["payload"])
            elif route.attack_location == "form" and form is not None:
                form[route.attack_field] = str(case["payload"])
            else:
                raise ValueError(f"incomplete attack field mapping for {route.route}")
            scenarios.append(
                Scenario(
                    route=route,
                    scenario=family,
                    test_id=f"m08-{run_id[:8]}-{serial}-{uuid4().hex[:8]}",
                    query=query,
                    form=form,
                    expected_prediction=expected,
                    catalog_case_id=str(case["case_id"]),
                )
            )
    return scenarios


def _file_offset(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _read_new_audit_events(path: Path, offset: int) -> tuple[int, list[dict[str, Any]]]:
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            if size < offset:
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
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(event, dict):
            events.append(event)
    return offset + consumed, events


def _audit_event_for_test(
    path: Path,
    *,
    offset: int,
    scenario: Scenario,
    origin: str,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any] | None]:
    deadline = time.monotonic() + timeout_seconds
    current_offset = offset
    expected = urlsplit(_scenario_url(origin, scenario))
    expected_query = parse_qs(expected.query, keep_blank_values=True)
    while time.monotonic() < deadline:
        current_offset, events = _read_new_audit_events(path, current_offset)
        for event in events:
            transaction = event.get("transaction")
            request = transaction.get("request") if isinstance(transaction, dict) else None
            uri = str(request.get("uri") or "") if isinstance(request, dict) else ""
            actual = urlsplit(uri)
            actual_query = parse_qs(actual.query, keep_blank_values=True)
            actual_method = str(request.get("method") or "").upper() if isinstance(request, dict) else ""
            if (
                actual.path == expected.path
                and actual_query == expected_query
                and (not actual_method or actual_method == scenario.route.method)
            ):
                return current_offset, event
        time.sleep(0.1)
    return current_offset, None


def _audit_metadata(event: dict[str, Any] | None) -> dict[str, Any]:
    transaction = event.get("transaction") if event else None
    if not isinstance(transaction, dict):
        return {}
    request = transaction.get("request")
    request = request if isinstance(request, dict) else {}
    messages = transaction.get("messages")
    messages = messages if isinstance(messages, list) else []
    rule_ids: list[str] = []
    for message in messages:
        details = message.get("details") if isinstance(message, dict) else None
        if isinstance(details, dict) and details.get("ruleId") is not None:
            rule_ids.append(str(details["ruleId"]))
    try:
        score = int(transaction.get("anomaly_score"))
    except (TypeError, ValueError):
        score = None
    return {
        "transaction_id": str(transaction.get("unique_id") or transaction.get("id") or ""),
        "crs_score": score,
        "crs_rule_ids": list(dict.fromkeys(rule_ids)),
    }


def _http_request(
    opener,
    url: str,
    *,
    method: str = "GET",
    form: dict[str, str] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    headers = {
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-store",
        "User-Agent": "cybertrace-local-multi-route-tester/1.0",
    }
    data = None
    if method == "POST":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form or {}).encode("utf-8")
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(256 * 1024)
            return {
                "status": int(response.status),
                "headers": response.headers,
                "body": body,
                "error": None,
            }
    except HTTPError as exc:
        try:
            body = exc.read(256 * 1024)
        finally:
            headers = exc.headers
            status = int(exc.code)
            exc.close()
        return {"status": status, "headers": headers, "body": body, "error": None}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": None, "headers": {}, "body": b"", "error": type(exc).__name__}


def _json_request(opener, url: str, *, api_key: str, timeout_seconds: float) -> tuple[dict[str, Any] | None, str | None]:
    request = Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            value = json.loads(response.read(128 * 1024).decode("utf-8"))
            return (value, None) if isinstance(value, dict) else (None, "invalid_json_shape")
    except HTTPError as exc:
        status = int(exc.code)
        exc.close()
        return None, f"http_{status}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _poll_lookup(
    opener,
    backend: str,
    transaction_id: str,
    *,
    api_key: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any] | None, str | None]:
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    endpoint = f"{backend}/api/internal/waf-events/{transaction_id}"
    while time.monotonic() < deadline:
        payload, error = _json_request(
            opener, endpoint, api_key=api_key, timeout_seconds=min(5.0, timeout_seconds)
        )
        last_error = error
        if payload and payload.get("found") is True and payload.get("status") != "PROCESSING":
            return payload, None
        if error and error.startswith("http_"):
            return None, error
        time.sleep(0.15)
    return None, last_error or "backend_lookup_timeout"


def _scenario_url(origin: str, scenario: Scenario) -> str:
    query = dict(scenario.query)
    if scenario.route.method == "POST" and scenario.scenario in ATTACK_LABELS:
        # CRS audit correlation needs a request-URI marker for POST bodies. The
        # direct portal bridge deliberately ignores query data, so this marker
        # never enters the form-field model input.
        query["__cybertrace_test_id"] = scenario.test_id
    encoded = urlencode(query)
    return f"{origin}{scenario.route.path}?{encoded}" if encoded else f"{origin}{scenario.route.path}"


def _safe_redirect(origin: str, location: str) -> str | None:
    target = urljoin(f"{origin}/", location)
    parsed = urlsplit(target)
    origin_host = urlsplit(origin).hostname
    if parsed.scheme != "http" or parsed.hostname != origin_host or parsed.port != urlsplit(origin).port:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _observed_http_effect(status: int | None, crs_rule_ids: list[str]) -> str:
    if status == 403 and crs_rule_ids:
        return "MODSECURITY_BLOCKED"
    if status == 429:
        return "HTTP_THROTTLED"
    if status == 403:
        return "HTTP_FORBIDDEN_WITHOUT_CRS_EVIDENCE"
    if status in REDIRECT_CODES:
        return "APPLICATION_REDIRECT"
    return "NO_HTTP_BLOCK_OR_THROTTLE_OBSERVED"


def _run_scenario(
    scenario: Scenario,
    *,
    opener,
    origin: str,
    backend: str,
    audit_log: Path,
    api_key: str,
    request_timeout_seconds: float,
    audit_timeout_seconds: float,
    lookup_timeout_seconds: float,
    run_id: str,
) -> dict[str, Any]:
    audit_offset = _file_offset(audit_log)
    response = _http_request(
        opener,
        _scenario_url(origin, scenario),
        method=scenario.route.method,
        form=scenario.form,
        timeout_seconds=request_timeout_seconds,
    )
    headers = response["headers"]
    edge_id = headers.get("X-CyberTrace-Transaction-ID", "") if headers else ""
    follow_status = None
    operation_completed = (
        response["status"] is not None and 200 <= response["status"] < 300
    )
    followed = None
    if (
        scenario.route.follows_success_redirect
        and response["status"] in REDIRECT_CODES
        and headers
    ):
        redirect = _safe_redirect(origin, headers.get("Location", ""))
        if redirect:
            followed = _http_request(
                opener,
                redirect,
                timeout_seconds=request_timeout_seconds,
            )
            follow_status = followed["status"]
            operation_completed = follow_status is not None and 200 <= follow_status < 300
        else:
            operation_completed = False

    response_marker_match = None
    if scenario.scenario == "normal" and scenario.route.normal_response_marker:
        final_body = followed["body"] if followed else response["body"]
        body_text = final_body.decode("utf-8", errors="replace")
        response_marker_match = scenario.route.normal_response_marker in body_text
        operation_completed = operation_completed and response_marker_match

    _, audit_event = _audit_event_for_test(
        audit_log,
        offset=audit_offset,
        scenario=scenario,
        origin=origin,
        timeout_seconds=audit_timeout_seconds,
    )
    audit = _audit_metadata(audit_event)
    transaction_id = audit.get("transaction_id") or edge_id
    lookup = None
    lookup_error = None
    if transaction_id:
        lookup, lookup_error = _poll_lookup(
            opener,
            backend,
            str(transaction_id),
            api_key=api_key,
            timeout_seconds=lookup_timeout_seconds,
        )

    prediction = str(lookup.get("prediction") or "") if lookup else ""
    expected = scenario.expected_prediction
    classification_match = bool(expected and prediction == expected)
    observed_http_effect = _observed_http_effect(
        response["status"], audit.get("crs_rule_ids", [])
    )
    return {
        "run_id": run_id,
        "test_id": scenario.test_id,
        "route": scenario.route.route,
        "method": scenario.route.method,
        "scenario": scenario.scenario,
        "catalog_case_id": scenario.catalog_case_id,
        "http_status": response["status"],
        "follow_status": follow_status,
        "operation_completed": operation_completed if scenario.scenario == "normal" else None,
        "response_marker_match": response_marker_match,
        "transaction_id": str(transaction_id or ""),
        "ingest_source": lookup.get("ingest_source") if lookup else None,
        "source_provenance": lookup.get("source_provenance") if lookup else None,
        "source_verification_status": lookup.get("source_verification_status") if lookup else None,
        "bridge_found": bool(lookup and lookup.get("found") is True),
        "bridge_status": lookup.get("status") if lookup else None,
        "prediction": prediction or None,
        "model_version": lookup.get("model_version") if lookup else None,
        "confidence": lookup.get("confidence") if lookup else None,
        "confidence_level": lookup.get("confidence_level") if lookup else None,
        "ml_action_recommendation": lookup.get("action_taken") if lookup else None,
        "recorded_policy_decision": lookup.get("policy_decision") if lookup else None,
        "recorded_policy_decision_reason": lookup.get("policy_decision_reason") if lookup else None,
        "observed_http_effect": observed_http_effect,
        "crs_score": audit.get("crs_score"),
        "crs_rule_ids": audit.get("crs_rule_ids", []),
        "expected_prediction": expected,
        "classification_match": classification_match if lookup else None,
        "alert_id": lookup.get("alert_id") if lookup else None,
        "alert_visible_in_api": None,
        "request_error": response["error"] or lookup_error,
    }


def _write_report(output_dir: Path, run_id: str, rows: list[dict[str, Any]], metadata: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{run_id}.json"
    csv_path = output_dir / f"{run_id}.csv"
    json_path.write_text(
        json.dumps({"metadata": metadata, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def run(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    api_key = os.environ.get("API_SECRET_KEY", "")
    if not api_key:
        raise ValueError("API_SECRET_KEY must be available in the isolated backend container")
    origin = validate_origin(args.origin, allowed_hosts=ALLOWED_ORIGIN_HOSTS, label="origin")
    backend = validate_origin(args.backend, allowed_hosts=ALLOWED_BACKEND_HOSTS, label="backend")
    catalog = load_catalog(args.catalog)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    scenarios = build_scenarios(catalog, run_id=run_id)
    opener = _opener()
    rows: list[dict[str, Any]] = []
    previous_request = time.monotonic()
    for scenario in scenarios:
        wait = 1 / args.max_rps - (time.monotonic() - previous_request)
        if wait > 0:
            time.sleep(wait)
        previous_request = time.monotonic()
        row = _run_scenario(
            scenario,
            opener=opener,
            origin=origin,
            backend=backend,
            audit_log=args.audit_log,
            api_key=api_key,
            request_timeout_seconds=args.request_timeout,
            audit_timeout_seconds=args.audit_timeout,
            lookup_timeout_seconds=args.lookup_timeout,
            run_id=run_id,
        )
        rows.append(row)
        print(json.dumps({key: row[key] for key in (
            "route", "method", "scenario", "http_status", "follow_status",
            "operation_completed", "response_marker_match",
            "transaction_id", "ingest_source", "source_verification_status",
            "prediction", "model_version", "confidence_level",
            "ml_action_recommendation", "recorded_policy_decision",
            "observed_http_effect", "crs_rule_ids", "bridge_found",
        )}, separators=(",", ":")), flush=True)

    stats, stats_error = _json_request(
        opener,
        f"{backend}/api/stats",
        api_key=api_key,
        timeout_seconds=args.request_timeout,
    )
    alerts, alerts_error = _json_request(
        opener,
        f"{backend}/api/alerts?page=1&page_size=100",
        api_key=api_key,
        timeout_seconds=args.request_timeout,
    )
    alert_ids = {
        str(item.get("id"))
        for item in (alerts or {}).get("items", [])
        if isinstance(item, dict) and item.get("id") is not None
    }
    for row in rows:
        if row.get("alert_id") is not None:
            row["alert_visible_in_api"] = str(row["alert_id"]) in alert_ids

    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "environment": "isolated-local-compose",
        "origin": origin,
        "enforcement_mode": "shadow",
        "action_semantics": "ML and policy fields are recorded recommendations; observed_http_effect reports the response actually returned by the isolated test path.",
        "catalog_version": catalog.get("catalog_version"),
        "requests": len(rows),
        "normal_requests": sum(row["scenario"] == "normal" for row in rows),
        "attack_requests": sum(row["scenario"] != "normal" for row in rows),
        "persisted_events": sum(row["bridge_found"] for row in rows),
        "classification_matches": sum(row["classification_match"] is True for row in rows),
        "alert_list_count": len(alert_ids),
        "stats_total_requests": (stats or {}).get("total_requests"),
        "stats_error": stats_error,
        "alerts_error": alerts_error,
        "bounded_rps": args.max_rps,
        "public_endpoint_allowed": False,
        "submitted_values_in_report": False,
    }
    return metadata, rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exercise M7/M8 WAF-ML coverage across local portal routes.")
    parser.add_argument("--catalog", type=Path, default=Path("scripts/fixtures/search_records_attack_catalog.json"))
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--audit-log", type=Path, default=Path(DEFAULT_AUDIT_LOG))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-rps", type=float, default=0.5)
    parser.add_argument("--request-timeout", type=float, default=15.0)
    parser.add_argument("--audit-timeout", type=float, default=1.0)
    parser.add_argument("--lookup-timeout", type=float, default=8.0)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not 0 < args.max_rps <= 2:
        parser.error("--max-rps must be greater than 0 and no more than 2")
    if not 0 < args.request_timeout <= 60:
        parser.error("--request-timeout must be between 0 and 60 seconds")
    if not 0 <= args.audit_timeout <= 10 or not 0 < args.lookup_timeout <= 30:
        parser.error("audit/lookup timeouts exceed the bounded runner limits")
    try:
        metadata, rows = run(args)
        json_path, csv_path = _write_report(args.output_dir, metadata["run_id"], rows, metadata)
    except (ValueError, OSError) as exc:
        print(f"tester_error={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"metadata": metadata, "json_report": str(json_path), "csv_report": str(csv_path)}, separators=(",", ":")))
    has_unverified = any(not row["bridge_found"] for row in rows)
    has_normal_failure = any(row["scenario"] == "normal" and not row["operation_completed"] for row in rows)
    has_attack_miss = any(row["scenario"] != "normal" and row["classification_match"] is not True for row in rows)
    return 1 if has_unverified or has_normal_failure or has_attack_miss else 0


if __name__ == "__main__":
    raise SystemExit(main())
