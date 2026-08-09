from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URLS = {
    "backend": "http://127.0.0.1:8000",
    "waf-8088": "http://localhost:8088",
    "demo-target-8089": "http://localhost:8089",
}
DEFAULT_AUDIT_LOGS = {
    "waf-8088": REPO_ROOT / "logs" / "modsecurity" / "modsec_audit.jsonl",
    "demo-target-8089": (
        REPO_ROOT
        / "logs"
        / "modsecurity"
        / "demo-target"
        / "modsec_audit.jsonl"
    ),
}
BACKEND_LOOKUP_MAX_ATTEMPTS = 20
BACKEND_LOOKUP_RETRY_INTERVAL_SECONDS = 0.25
AUDIT_LOOKUP_MAX_ATTEMPTS = 20
AUDIT_LOOKUP_RETRY_INTERVAL_SECONDS = 0.25


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    details: str
    required: bool = True
    correlated: bool | None = None
    transaction_id: str | None = None


def _new_marker() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"CYBERTRACE_SMOKE_{timestamp}_{uuid4().hex}"


def _request_status(url: str, timeout: float) -> int:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CyberTrace-final-demo-smoke/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectionError("service unavailable") from exc


def _http_check(
    name: str,
    base_url: str,
    path: str,
    expected_status: int,
    timeout: float,
) -> CheckResult:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        actual_status = _request_status(url, timeout)
    except Exception:
        return CheckResult(
            name=name,
            status="FAIL",
            details="service unavailable or timed out",
        )

    if actual_status == expected_status:
        return CheckResult(
            name=name,
            status="PASS",
            details=f"HTTP {actual_status}",
        )
    return CheckResult(
        name=name,
        status="FAIL",
        details=f"expected HTTP {expected_status}, got {actual_status}",
    )


def _audit_log_offset(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0
    except OSError:
        return 0


def _read_new_audit_events(
    path: Path,
    *,
    start_offset: int,
) -> tuple[list[dict], int, str | None]:
    if not path.exists():
        return [], start_offset, None

    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            if size < start_offset:
                return [], size, "audit log was truncated after the smoke cursor"
            handle.seek(start_offset)
            data = handle.read()
    except OSError as exc:
        return [], start_offset, f"audit log could not be read: {type(exc).__name__}"

    complete_lines: list[bytes] = []
    consumed = 0
    for raw_line in data.splitlines(keepends=True):
        if not raw_line.endswith((b"\n", b"\r")):
            break
        complete_lines.append(raw_line)
        consumed += len(raw_line)

    events: list[dict] = []
    for raw_line in complete_lines:
        line = raw_line.strip()
        if not line:
            continue
        try:
            decoded = line.decode("utf-8")
        except UnicodeDecodeError:
            return [], start_offset + consumed, "new audit event is not valid UTF-8"
        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError:
            return [], start_offset + consumed, "new audit event is not valid JSON"
        if not isinstance(payload, dict):
            return [], start_offset + consumed, "new audit event is not a JSON object"
        events.append(payload)

    return events, start_offset + consumed, None


def _audit_event_details(
    payload: dict,
) -> tuple[str | None, int | None, str | None, str | None]:
    transaction = payload.get("transaction")
    if not isinstance(transaction, dict):
        transaction = {}
    request = transaction.get("request")
    if not isinstance(request, dict):
        request = {}
    response = transaction.get("response")
    if not isinstance(response, dict):
        response = {}

    transaction_id = transaction.get("unique_id") or transaction.get("id")
    transaction_id = transaction_id or payload.get("transaction_id")
    uri = request.get("uri") or payload.get("request_uri")
    request_path = payload.get("request_path")
    if not isinstance(request_path, str) or not request_path:
        request_path = urlsplit(str(uri)).path if uri is not None else None
    query_string = payload.get("query_string")
    if not isinstance(query_string, str):
        query_string = urlsplit(str(uri)).query if uri is not None else None

    raw_status = (
        response.get("http_code")
        or transaction.get("response_status")
        or payload.get("response_status")
        or payload.get("status")
    )
    try:
        response_status = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        response_status = None

    return (
        str(transaction_id).strip() if transaction_id is not None else None,
        response_status,
        request_path,
        query_string,
    )


def _check_audit_log(
    path: Path,
    *,
    start_offset: int,
    expected_path: str,
    expected_query: str | None = None,
    expected_status: int,
    check_name: str = "audit_transaction",
) -> CheckResult:
    if not path.exists():
        return CheckResult(
            name=check_name,
            status="FAIL",
            details="audit JSONL not found",
            required=True,
            correlated=False,
        )

    try:
        events, _, error = _read_new_audit_events(
            path,
            start_offset=start_offset,
        )
    except (OSError, ValueError):
        error = "audit JSONL could not be inspected"
        events = []
    if error:
        return CheckResult(
            name=check_name,
            status="FAIL",
            details=error,
            correlated=False,
        )

    request_label = _audit_request_label(expected_path, expected_query)
    matching_payload = None
    matching_transaction_id = None
    for payload in events:
        (
            transaction_id,
            response_status,
            request_path,
            query_string,
        ) = _audit_event_details(payload)
        if (
            request_path == expected_path
            and (expected_query is None or query_string == expected_query)
            and response_status == expected_status
        ):
            matching_payload = payload
            matching_transaction_id = transaction_id

    if matching_payload is None:
        return CheckResult(
            name=check_name,
            status="FAIL",
            details=(
                "new audit event for "
                f"{request_label} "
                f"with HTTP {expected_status} "
                "was not found"
            ),
            correlated=False,
        )

    if not matching_transaction_id:
        return CheckResult(
            name=check_name,
            status="FAIL",
            details="correlated audit event has no transaction_id",
            correlated=False,
        )

    return CheckResult(
        name=check_name,
        status="PASS",
        details=(
            "new audit event for "
            f"{request_label} "
            f"with HTTP {expected_status} "
            "has a transaction_id"
        ),
        correlated=True,
        transaction_id=matching_transaction_id,
    )


def _wait_for_audit_log(
    path: Path,
    *,
    start_offset: int,
    expected_path: str,
    expected_query: str | None = None,
    expected_status: int,
    check_name: str = "audit_transaction",
) -> CheckResult:
    result = None
    for attempt in range(AUDIT_LOOKUP_MAX_ATTEMPTS):
        result = _check_audit_log(
            path=path,
            start_offset=start_offset,
            expected_path=expected_path,
            expected_query=expected_query,
            expected_status=expected_status,
            check_name=check_name,
        )
        if result.status == "PASS":
            return result
        if attempt + 1 < AUDIT_LOOKUP_MAX_ATTEMPTS:
            time.sleep(AUDIT_LOOKUP_RETRY_INTERVAL_SECONDS)
    assert result is not None
    return result


def _audit_request_label(expected_path: str, expected_query: str | None) -> str:
    if expected_query is None:
        return expected_path
    return f"{expected_path}?{expected_query}"


def _run_backend_lookup(transaction_id: str) -> dict:
    lookup_script = (
        "import os, urllib.parse, urllib.request;"
        "txid=os.environ['TXID'];"
        "secret=os.environ['API_SECRET_KEY'];"
        "url='http://127.0.0.1:8000/api/internal/waf-events/'"
        "+urllib.parse.quote(txid, safe='');"
        "req=urllib.request.Request(url,headers={'Authorization':'Bearer '+secret});"
        "print(urllib.request.urlopen(req,timeout=10).read().decode())"
    )
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "-e",
            f"TXID={transaction_id}",
            "backend",
            "python",
            "-c",
            lookup_script,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
        cwd=REPO_ROOT,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("backend lookup did not return an object")
    return payload


def _run_backend_internal_health(timeout: float) -> dict:
    health_timeout = float(timeout)
    health_script = (
        "import json, urllib.request;"
        "result={};"
        "\nfor key,path in [('health','/health'),('api_health','/api/health')]:"
        "\n  with urllib.request.urlopen("
        f"'http://127.0.0.1:8000'+path, timeout={health_timeout!r}) as response:"
        "\n    result[key]=response.status"
        "\nprint(json.dumps(result))"
    )
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            health_script,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=max(1.0, health_timeout * 2 + 1.0),
        cwd=REPO_ROOT,
    )
    output_lines = [
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    ]
    if not output_lines:
        raise ValueError("backend health check returned no JSON")
    payload = json.loads(output_lines[-1])
    if not isinstance(payload, dict):
        raise ValueError("backend health check did not return an object")
    return payload


def _backend_internal_health_checks(timeout: float) -> list[CheckResult]:
    try:
        payload = _run_backend_internal_health(timeout)
    except Exception:  # noqa: BLE001
        return [
            CheckResult(
                name="backend_health",
                status="FAIL",
                details=(
                    "Docker-internal backend health check was unavailable or invalid"
                ),
            ),
            CheckResult(
                name="backend_api_health",
                status="FAIL",
                details=(
                    "Docker-internal backend health check was unavailable or invalid"
                ),
            ),
        ]

    checks = []
    for name, key in (
        ("backend_health", "health"),
        ("backend_api_health", "api_health"),
    ):
        status = payload.get(key)
        checks.append(
            CheckResult(
                name=name,
                status="PASS" if status == 200 else "FAIL",
                details=f"HTTP {status}" if status is not None else "missing status",
            )
        )
    return checks


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_backend_lookup(
    payload: dict,
    *,
    transaction_id: str,
    started_at: datetime,
    expected_path: str,
    expected_prediction: str | None = None,
    require_non_normal_prediction: bool = False,
    expected_action: str | None = None,
    check_name: str = "backend_transaction_lookup",
) -> CheckResult:
    timestamp = _parse_timestamp(payload.get("timestamp"))
    request_path = payload.get("request_path")
    earliest_current_timestamp = started_at.astimezone(timezone.utc).replace(
        microsecond=0
    )
    correlated = (
        payload.get("found") is True
        and payload.get("transaction_id") == transaction_id
        and request_path == expected_path
        and timestamp is not None
        and timestamp >= earliest_current_timestamp
    )
    if expected_prediction is not None:
        correlated = correlated and payload.get("prediction") == expected_prediction
    if require_non_normal_prediction:
        correlated = correlated and payload.get("prediction") not in (None, "Normal")
    if expected_action is not None:
        correlated = correlated and payload.get("action_taken") == expected_action
    if not correlated:
        expected_policy = []
        if expected_prediction is not None:
            expected_policy.append(f"prediction={expected_prediction}")
        if require_non_normal_prediction:
            expected_policy.append("prediction=non-Normal")
        if expected_action is not None:
            expected_policy.append(f"action={expected_action}")
        policy_details = (
            f"; observed prediction={payload.get('prediction')}, "
            f"action={payload.get('action_taken')}"
            + (f"; expected {', '.join(expected_policy)}" if expected_policy else "")
        )
        return CheckResult(
            name=check_name,
            status="FAIL",
            details=(
                "backend record is stale, has the wrong request path, or does not "
                "match the expected classification/action"
                + policy_details
            ),
            correlated=False,
            transaction_id=transaction_id,
        )
    return CheckResult(
        name=check_name,
        status="PASS",
        details=(
            "backend record matches the transaction, path, timestamp, and "
            "expected policy"
        ),
        correlated=True,
        transaction_id=transaction_id,
    )


def _backend_lookup_check(
    *,
    transaction_id: str | None,
    started_at: datetime,
    required: bool,
    expected_path: str,
    expected_prediction: str | None = None,
    require_non_normal_prediction: bool = False,
    expected_action: str | None = None,
    check_name: str = "backend_transaction_lookup",
) -> CheckResult:
    if not required:
        return CheckResult(
            name=check_name,
            status="SKIP",
            details=(
                "backend lookup was not requested; this is audit-only proof, "
                "not full WAF-to-backend proof"
            ),
            required=False,
            correlated=False,
            transaction_id=transaction_id,
        )
    if not transaction_id:
        return CheckResult(
            name=check_name,
            status="FAIL",
            details="backend lookup requires a correlated transaction_id",
            correlated=False,
        )
    result = None
    for attempt in range(BACKEND_LOOKUP_MAX_ATTEMPTS):
        try:
            payload = _run_backend_lookup(transaction_id)
        except Exception:  # noqa: BLE001
            return CheckResult(
                name=check_name,
                status="FAIL",
                details="Docker-internal backend lookup was unavailable or invalid",
                correlated=False,
                transaction_id=transaction_id,
            )
        result = _validate_backend_lookup(
            payload,
            transaction_id=transaction_id,
            started_at=started_at,
            expected_path=expected_path,
            expected_prediction=expected_prediction,
            require_non_normal_prediction=require_non_normal_prediction,
            expected_action=expected_action,
            check_name=check_name,
        )
        if result.status == "PASS":
            return result
        if attempt + 1 < BACKEND_LOOKUP_MAX_ATTEMPTS:
            time.sleep(BACKEND_LOOKUP_RETRY_INTERVAL_SECONDS)
    assert result is not None
    return result


def run_checks(
    mode: str,
    *,
    base_url: str,
    timeout: float,
    audit_log: Path | None,
    marker: str,
    started_at: datetime,
    require_backend_lookup: bool,
    audit_start_offset: int = 0,
    backend_internal: bool = False,
) -> list[CheckResult]:
    if mode == "backend":
        if backend_internal:
            return _backend_internal_health_checks(timeout)
        return [
            _http_check("backend_health", base_url, "/health", 200, timeout),
            _http_check(
                "backend_api_health",
                base_url,
                "/api/health",
                200,
                timeout,
            ),
        ]

    if mode == "waf-8088":
        audit_path = audit_log or DEFAULT_AUDIT_LOGS[mode]
        checks = [
            _http_check("waf_healthz", base_url, "/healthz", 200, timeout),
            _http_check("waf_api_health", base_url, "/api/health", 200, timeout),
            _http_check(
                "waf_sqli_block",
                base_url,
                "/api/health?id=17%27%20OR%2017%3D17--",
                403,
                timeout,
            ),
        ]
        audit_check = _wait_for_audit_log(
            path=audit_path,
            start_offset=audit_start_offset,
            expected_path="/api/health",
            expected_query="id=17%27%20OR%2017%3D17--",
            expected_status=403,
            check_name="audit_transaction",
        )
        checks.append(audit_check)
        checks.append(
            _backend_lookup_check(
                transaction_id=audit_check.transaction_id,
                started_at=started_at,
                required=require_backend_lookup,
                expected_path="/api/health",
                require_non_normal_prediction=True,
                expected_action="BLOCKED",
            )
        )
        return checks

    audit_path = audit_log or DEFAULT_AUDIT_LOGS[mode]
    checks = [
        _http_check("demo_target_home", base_url, "/", 200, timeout),
        _http_check(
            "demo_target_normal",
            base_url,
            "/records/search?query=Maple",
            200,
            timeout,
        ),
    ]
    normal_audit = _wait_for_audit_log(
        path=audit_path,
        start_offset=audit_start_offset,
        expected_path="/records/search",
        expected_query="query=Maple",
        expected_status=200,
        check_name="audit_transaction_normal",
    )
    checks.append(normal_audit)
    checks.append(
        _backend_lookup_check(
            transaction_id=normal_audit.transaction_id,
            started_at=started_at,
            required=require_backend_lookup,
            expected_path="/records/search",
            expected_prediction="Normal",
            expected_action="ALLOWED",
            check_name="backend_transaction_lookup_normal",
        )
    )

    attack_start_offset = _audit_log_offset(audit_path)
    checks.extend(
        [
        _http_check(
            "demo_target_attack",
            base_url,
            "/records/search?query=%27%20UNION%20SELECT%20null,null,null--",
            403,
            timeout,
        ),
        ]
    )
    attack_audit = _wait_for_audit_log(
        path=audit_path,
        start_offset=attack_start_offset,
        expected_path="/records/search",
        expected_query="%27%20UNION%20SELECT%20null,null,null--",
        expected_status=403,
        check_name="audit_transaction_attack",
    )
    checks.append(attack_audit)
    checks.append(
        _backend_lookup_check(
            transaction_id=attack_audit.transaction_id,
            started_at=started_at,
            required=require_backend_lookup,
            expected_path="/records/search",
            require_non_normal_prediction=True,
            expected_action="BLOCKED",
            check_name="backend_transaction_lookup_attack",
        )
    )
    return checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run explicit final-demo backend or local WAF smoke checks."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=tuple(DEFAULT_BASE_URLS),
        help="Explicit smoke target; Docker-backed modes never run implicitly.",
    )
    parser.add_argument(
        "--base-url",
        help="Override the selected mode's default base URL.",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        help="Override the local ModSecurity audit JSONL path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds. Default: 10.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one parseable JSON summary.",
    )
    parser.add_argument(
        "--require-backend-lookup",
        action="store_true",
        help=(
            "Require current transaction correlation through the Docker-internal "
            "backend lookup; valid only for WAF modes."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.require_backend_lookup and args.mode == "backend":
        parser.error("--require-backend-lookup requires a WAF mode")

    base_url = args.base_url or DEFAULT_BASE_URLS[args.mode]
    marker = _new_marker()
    started_at = datetime.now(timezone.utc)
    audit_path = args.audit_log or DEFAULT_AUDIT_LOGS.get(args.mode)
    audit_start_offset = _audit_log_offset(audit_path) if audit_path else 0
    checks = run_checks(
        args.mode,
        base_url=base_url,
        timeout=args.timeout,
        audit_log=args.audit_log,
        marker=marker,
        started_at=started_at,
        require_backend_lookup=args.require_backend_lookup,
        audit_start_offset=audit_start_offset,
        backend_internal=args.mode == "backend" and args.base_url is None,
    )
    passed = not any(check.required and check.status == "FAIL" for check in checks)
    warnings = [
        check.details
        for check in checks
        if not check.required and check.status in {"SKIP", "WARN"}
    ]
    failures = [
        check.details
        for check in checks
        if check.required and check.status == "FAIL"
    ]
    status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    audit_checks = [
        check for check in checks if check.name.startswith("audit_transaction")
    ]
    backend_checks = [
        check
        for check in checks
        if check.name.startswith("backend_transaction_lookup")
    ]
    audit_correlated = bool(audit_checks) and all(
        check.required and check.correlated is True for check in audit_checks
    )
    backend_correlated = bool(backend_checks) and all(
        check.required and check.correlated is True for check in backend_checks
    )

    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "status": status,
                    "passed": passed,
                    "marker": marker,
                    "audit_correlated": audit_correlated,
                    "backend_correlated": backend_correlated,
                    "warnings": warnings,
                    "failures": failures,
                    "checks": [asdict(check) for check in checks],
                },
                separators=(",", ":"),
            )
        )
    else:
        for check in checks:
            print(f"{check.name}: {check.status} - {check.details}")
        print(f"MARKER: {marker}")
        print(f"SUMMARY: {status}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
