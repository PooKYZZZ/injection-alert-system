from __future__ import annotations

import os

import pytest

from tests.e2e.pr7_block3_lifecycle_harness import require_block3bc_artifacts


@pytest.mark.skipif(
    os.environ.get("PR7_RUN_BLOCK3_PREFLIGHT") != "1",
    reason="set PR7_RUN_BLOCK3_PREFLIGHT=1 to verify locked local inputs",
)
def test_block3bc_preflight_verifies_model_portal_and_compose_inputs() -> None:
    lock = require_block3bc_artifacts()
    assert lock["model"]["model_version"]
    assert lock["portal"]["commit"]
    assert lock["containers"]
