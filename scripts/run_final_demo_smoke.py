from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
from urllib.parse import quote
import urllib.request
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


def _check_audit_log(path: Path, marker: str) -> CheckResult:
    if not path.exists():
        return CheckResult(
            name="audit_transaction",
            status="SKIP",
            details="audit JSONL not found",
            required=False,
            correlated=False,
        )

    try:
        matching_payload = None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if marker not in line:
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("audit JSONL entry is not an object")
                matching_payload = payload
    except (OSError, ValueError):
        return CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="marker-correlated audit JSONL entry is unavailable or invalid",
            correlated=False,
        )

    if matching_payload is None:
        return CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="current smoke marker was not found in the audit JSONL",
            correlated=False,
        )

    transaction = matching_payload.get("transaction")
    transaction_id = None
    if isinstance(transaction, dict):
        transaction_id = transaction.get("unique_id") or transaction.get("id")
    transaction_id = transaction_id or matching_payload.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        return CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="marker-correlated audit JSONL entry has no transaction_id",
            correlated=False,
        )

    return CheckResult(
        name="audit_transaction",
        status="PASS",
        details="current marker and transaction_id are correlated",
        correlated=True,
        transaction_id=transaction_id.strip(),
    )


def _wait_for_audit_log(path: Path, marker: str) -> CheckResult:
    result = None
    for attempt in range(AUDIT_LOOKUP_MAX_ATTEMPTS):
        result = _check_audit_log(path, marker)
        if result.status == "PASS":
            return result
        if attempt + 1 < AUDIT_LOOKUP_MAX_ATTEMPTS:
            time.sleep(AUDIT_LOOKUP_RETRY_INTERVAL_SECONDS)
    assert result is not None
    return result


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
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("backend lookup did not return an object")
    return payload


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
    marker: str,
    started_at: datetime,
) -> CheckResult:
    timestamp = _parse_timestamp(payload.get("timestamp"))
    query_string = payload.get("query_string")
    earliest_current_timestamp = started_at.astimezone(timezone.utc).replace(
        microsecond=0
    )
    correlated = (
        payload.get("found") is True
        and payload.get("transaction_id") == transaction_id
        and isinstance(query_string, str)
        and marker in query_string
        and timestamp is not None
        and timestamp >= earliest_current_timestamp
    )
    if not correlated:
        return CheckResult(
            name="backend_transaction_lookup",
            status="FAIL",
            details="backend record is stale or does not match the current marker",
            correlated=False,
            transaction_id=transaction_id,
        )
    return CheckResult(
        name="backend_transaction_lookup",
        status="PASS",
        details="backend record matches the current marker and smoke start time",
        correlated=True,
        transaction_id=transaction_id,
    )


def _backend_lookup_check(
    *,
    transaction_id: str | None,
    marker: str,
    started_at: datetime,
    required: bool,
) -> CheckResult:
    if not required:
        return CheckResult(
            name="backend_transaction_lookup",
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
            name="backend_transaction_lookup",
            status="FAIL",
            details="backend lookup requires a marker-correlated transaction_id",
            correlated=False,
        )
    result = None
    for attempt in range(BACKEND_LOOKUP_MAX_ATTEMPTS):
        try:
            payload = _run_backend_lookup(transaction_id)
        except Exception:  # noqa: BLE001
            return CheckResult(
                name="backend_transaction_lookup",
                status="FAIL",
                details="Docker-internal backend lookup was unavailable or invalid",
                correlated=False,
                transaction_id=transaction_id,
            )
        result = _validate_backend_lookup(
            payload,
            transaction_id=transaction_id,
            marker=marker,
            started_at=started_at,
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
) -> list[CheckResult]:
    if mode == "backend":
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
        checks = [
            _http_check("waf_healthz", base_url, "/healthz", 200, timeout),
            _http_check("waf_api_health", base_url, "/api/health", 200, timeout),
            _http_check(
                "waf_sqli_block",
                base_url,
                (
                    "/api/health?id=17%27%20OR%2017%3D17--%20"
                    f"{quote(marker, safe='')}"
                ),
                403,
                timeout,
            ),
        ]
        audit_check = _wait_for_audit_log(
            audit_log or DEFAULT_AUDIT_LOGS[mode],
            marker,
        )
        checks.append(audit_check)
        checks.append(
            _backend_lookup_check(
                transaction_id=audit_check.transaction_id,
                marker=marker,
                started_at=started_at,
                required=require_backend_lookup,
            )
        )
        return checks

    checks = [
        _http_check("demo_target_home", base_url, "/", 200, timeout),
        _http_check(
            "demo_target_sqli_block",
            base_url,
            (
                "/records/search?query=%27%20UNION%20SELECT%20"
                f"null,null,null--%20{quote(marker, safe='')}"
            ),
            403,
            timeout,
        ),
    ]
    audit_check = _wait_for_audit_log(
        audit_log or DEFAULT_AUDIT_LOGS[mode],
        marker,
    )
    checks.append(audit_check)
    checks.append(
        _backend_lookup_check(
            transaction_id=audit_check.transaction_id,
            marker=marker,
            started_at=started_at,
            required=require_backend_lookup,
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
            "Require current marker correlation through the Docker-internal "
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
    checks = run_checks(
        args.mode,
        base_url=base_url,
        timeout=args.timeout,
        audit_log=args.audit_log,
        marker=marker,
        started_at=started_at,
        require_backend_lookup=args.require_backend_lookup,
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
    audit_check = next(
        (check for check in checks if check.name == "audit_transaction"),
        None,
    )
    backend_check = next(
        (check for check in checks if check.name == "backend_transaction_lookup"),
        None,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "status": status,
                    "passed": passed,
                    "marker": marker,
                    "audit_correlated": bool(
                        audit_check and audit_check.correlated
                    ),
                    "backend_correlated": bool(
                        backend_check and backend_check.correlated
                    ),
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
