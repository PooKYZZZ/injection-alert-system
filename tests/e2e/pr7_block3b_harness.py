from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

EVIDENCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class LiveProofPrerequisiteError(RuntimeError):
    """The guarded external proof cannot safely start yet."""


@dataclass(frozen=True, slots=True)
class ExternalProofConfig:
    hostname: str
    token_file: Path
    source_a_url: str
    source_b_url: str

    @classmethod
    def from_env(cls) -> "ExternalProofConfig":
        if os.environ.get("PR7_RUN_BLOCK3_LIVE") != "1":
            raise LiveProofPrerequisiteError(
                "set PR7_RUN_BLOCK3_LIVE=1 only for an authorized external proof"
            )
        hostname = os.environ.get("PR7_PROOF_HOSTNAME", "").strip()
        token_file = Path(os.environ.get("CLOUDFLARED_TARGET_TOKEN_FILE", ""))
        source_a_url = os.environ.get("PR7_SOURCE_A_URL", "").strip()
        source_b_url = os.environ.get("PR7_SOURCE_B_URL", "").strip()
        if not hostname or "." not in hostname:
            raise LiveProofPrerequisiteError("PR7_PROOF_HOSTNAME is required")
        if not token_file.is_file():
            raise LiveProofPrerequisiteError("Cloudflare token file is unavailable")
        if token_file.stat().st_size == 0:
            raise LiveProofPrerequisiteError("Cloudflare token file is empty")
        if not source_a_url or not source_b_url or source_a_url == source_b_url:
            raise LiveProofPrerequisiteError(
                "two distinct external source URLs are required"
            )
        return cls(hostname, token_file, source_a_url, source_b_url)


def validate_evidence_id(value: str) -> str:
    if not EVIDENCE_ID.fullmatch(value):
        raise ValueError("invalid evidence ID")
    return value


def classify_response(response: httpx.Response) -> str:
    if response.status_code in {301, 302, 303, 307, 308}:
        return "access_redirect"
    if response.status_code == 403 and response.headers.get("cf-mitigated"):
        return "cloudflare_access_or_edge"
    if response.status_code == 403 and "pr7" in response.text.lower():
        return "pr7_dynamic_waf"
    if response.status_code == 403:
        return "static_crs_or_unknown_waf"
    if response.status_code in {401, 429}:
        return "access_or_rate_limit"
    if response.status_code >= 500:
        return "upstream_failure"
    return "portal_or_allowed"


def request_fresh(url: str, *, evidence_id: str) -> tuple[int, str, dict[str, Any]]:
    validate_evidence_id(evidence_id)
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=15) as client:
        response = client.get(
            url,
            headers={"X-PR7-Evidence-ID": evidence_id},
        )
    return response.status_code, classify_response(response), {
        "content_length": len(response.content),
        "server": response.headers.get("server", ""),
    }
