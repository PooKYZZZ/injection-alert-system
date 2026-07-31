"""Run a guarded, privacy-safe external PR7 source probe."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx

from scripts.pr7_block3_evidence import utc_now, validate_id, write_json


def _url(base: str, params: dict[str, str] | None = None) -> str:
    if not params:
        return base
    parts = urlsplit(base)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ""))


def _request(
    url: str,
    *,
    evidence_id: str,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {"X-PR7-Evidence-ID": evidence_id}
    client_id = os.environ.get("PR7_ACCESS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PR7_ACCESS_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        headers.update(
            {
                "CF-Access-Client-Id": client_id,
                "CF-Access-Client-Secret": client_secret,
            }
        )
    if extra_headers:
        headers.update(extra_headers)
    started = time.perf_counter()
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=15) as client:
        response = client.get(url, headers=headers)
    status = response.status_code
    if status in {301, 302, 303, 307, 308}:
        classification = "access_redirect"
    elif status == 403 and response.headers.get("cf-mitigated"):
        classification = "cloudflare_access_or_edge"
    elif status == 403:
        classification = "waf_or_unknown_403"
    elif status >= 500:
        classification = "upstream_failure"
    elif status in {401, 429}:
        classification = "access_or_rate_limit"
    else:
        classification = "portal_or_allowed"
    return {
        "evidence_id": evidence_id,
        "timestamp_utc": utc_now(),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "status_code": status,
        "classification": classification,
        "server": response.headers.get("server", ""),
        "cf_ray_present": bool(response.headers.get("cf-ray")),
        "cf_mitigated_present": bool(response.headers.get("cf-mitigated")),
        "content_length": len(response.content),
    }


def run_source_agent(proof_url: str, run_id: str, source_label: str) -> dict[str, Any]:
    if os.environ.get("PR7_RUN_BLOCK3_LIVE") != "1":
        raise RuntimeError("set PR7_RUN_BLOCK3_LIVE=1 for external source probes")
    validate_id(run_id, label="run ID")
    validate_id(source_label, label="source label")
    cases = (
        ("normal", {}, None),
        (
            "forged_headers",
            {"proof_case": "forged_headers"},
            {
                "CF-Connecting-IP": "127.0.0.1",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            },
        ),
        ("approved_attack_seed", {"id": "1 OR 1=1--"}, None),
        ("harmless_matching_search", {"proof_case": "matching"}, None),
        ("wrong_path", {}, None),
        ("static_crs", {"id": "1 OR 1=1--"}, None),
    )
    results: list[dict[str, Any]] = []
    for name, params, headers in cases:
        path = proof_url
        if name == "wrong_path":
            parts = urlsplit(proof_url)
            path = urlunsplit((parts.scheme, parts.netloc, parts.path + "/", "", ""))
        evidence_id = f"{run_id}-{source_label}-{name}"
        results.append(
            {
                "scenario": name,
                "source_label": source_label,
                "result": _request(
                    _url(path, params),
                    evidence_id=evidence_id,
                    extra_headers=headers,
                ),
            }
        )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "source_label": source_label,
        "generated_at_utc": utc_now(),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(
        args.output,
        run_source_agent(args.proof_url, args.run_id, args.source_label),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
