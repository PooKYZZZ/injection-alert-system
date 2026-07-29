from __future__ import annotations

import os

import pytest

from tests.e2e.pr7_backend_waf_harness import run_backend_to_waf_test


@pytest.mark.skipif(
    not os.environ.get("PR7_RUN_BACKEND_WAF_E2E"),
    reason="set PR7_RUN_BACKEND_WAF_E2E=1 to run disposable Docker integration proof",
)
def test_real_critical_recommendation_reaches_local_waf() -> None:
    """Prove the live PostgreSQL -> backend snapshot -> WAF data-plane path."""
    run_backend_to_waf_test()
