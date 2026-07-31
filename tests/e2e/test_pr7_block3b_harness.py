from __future__ import annotations

import os

import httpx
import pytest

from tests.e2e.pr7_block3b_harness import (
    ExternalProofConfig,
    LiveProofPrerequisiteError,
    classify_response,
    validate_evidence_id,
)


def test_external_proof_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("PR7_RUN_BLOCK3_LIVE", raising=False)
    with pytest.raises(LiveProofPrerequisiteError, match="authorized"):
        ExternalProofConfig.from_env()


@pytest.mark.parametrize("value", ["", "bad id", "x\n", "a" * 81])
def test_external_evidence_id_is_strict(value: str) -> None:
    with pytest.raises(ValueError):
        validate_evidence_id(value)


def test_response_classifier_separates_access_dynamic_waf_and_portal() -> None:
    assert classify_response(httpx.Response(302, headers={"location": "/login"})) == "access_redirect"
    assert classify_response(httpx.Response(403, headers={"cf-mitigated": "challenge"})) == "cloudflare_access_or_edge"
    assert classify_response(httpx.Response(403, text="PR7 WAF block")) == "pr7_dynamic_waf"
    assert classify_response(httpx.Response(200, text="portal")) == "portal_or_allowed"
