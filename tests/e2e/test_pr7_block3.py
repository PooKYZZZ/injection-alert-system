from __future__ import annotations

import os

import pytest

from tests.e2e.pr7_block3_lifecycle_harness import run_block3_lifecycle


@pytest.mark.skipif(
    os.environ.get("PR7_RUN_BLOCK3_E2E") != "1",
    reason="set PR7_RUN_BLOCK3_E2E=1 to run the disposable Block 3 lifecycle",
)
def test_attack_to_critical_waf_block_lifecycle() -> None:
    run_block3_lifecycle()
