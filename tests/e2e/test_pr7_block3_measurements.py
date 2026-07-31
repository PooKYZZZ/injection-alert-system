from __future__ import annotations

import json

from tests.e2e.pr7_block3_measurements import run_capacity_measurements


def test_capacity_measurement_covers_required_boundaries(tmp_path) -> None:
    output = tmp_path / "capacity.json"
    result = run_capacity_measurements(output, repetitions=2)

    assert [level["entries"] for level in result["levels"]] == [0, 1, 64]
    assert all(level["samples"] == 2 for level in result["levels"])
    assert all(level["candidate_bytes"] > 0 for level in result["levels"])
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == 1
