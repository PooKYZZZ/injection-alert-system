from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request


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


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    details: str
    required: bool = True


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


def _check_audit_log(path: Path) -> CheckResult:
    if not path.exists():
        return CheckResult(
            name="audit_transaction",
            status="SKIP",
            details="audit JSONL not found",
            required=False,
        )

    try:
        latest_line = None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    latest_line = line
        if latest_line is None:
            raise ValueError("audit JSONL is empty")
        payload = json.loads(latest_line)
        if not isinstance(payload, dict):
            raise ValueError("audit JSONL entry is not an object")
    except (OSError, ValueError):
        return CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="latest audit JSONL entry is unavailable or invalid",
        )

    transaction = payload.get("transaction")
    transaction_id = None
    if isinstance(transaction, dict):
        transaction_id = transaction.get("unique_id") or transaction.get("id")
    transaction_id = transaction_id or payload.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        return CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="latest audit JSONL entry has no transaction_id",
        )

    return CheckResult(
        name="audit_transaction",
        status="PASS",
        details="transaction_id present",
    )


def _optional_backend_lookup() -> CheckResult:
    return CheckResult(
        name="backend_transaction_lookup",
        status="SKIP",
        details="optional Docker-internal lookup remains a manual runbook step",
        required=False,
    )


def run_checks(
    mode: str,
    *,
    base_url: str,
    timeout: float,
    audit_log: Path | None,
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
        return [
            _http_check("waf_healthz", base_url, "/healthz", 200, timeout),
            _http_check("waf_api_health", base_url, "/api/health", 200, timeout),
            _http_check(
                "waf_sqli_block",
                base_url,
                "/api/health?id=17%27%20OR%2017%3D17--",
                403,
                timeout,
            ),
            _check_audit_log(audit_log or DEFAULT_AUDIT_LOGS[mode]),
            _optional_backend_lookup(),
        ]

    return [
        _http_check("demo_target_home", base_url, "/", 200, timeout),
        _http_check(
            "demo_target_sqli_block",
            base_url,
            (
                "/records/search?query=%27%20UNION%20SELECT%20"
                "null,null,null--%20FINAL_DEMO_SMOKE"
            ),
            403,
            timeout,
        ),
        _check_audit_log(audit_log or DEFAULT_AUDIT_LOGS[mode]),
        _optional_backend_lookup(),
    ]


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    base_url = args.base_url or DEFAULT_BASE_URLS[args.mode]
    checks = run_checks(
        args.mode,
        base_url=base_url,
        timeout=args.timeout,
        audit_log=args.audit_log,
    )
    passed = not any(check.required and check.status == "FAIL" for check in checks)

    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "passed": passed,
                    "checks": [asdict(check) for check in checks],
                },
                separators=(",", ":"),
            )
        )
    else:
        for check in checks:
            print(f"{check.name}: {check.status} - {check.details}")
        print(f"SUMMARY: {'PASS' if passed else 'FAIL'}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
