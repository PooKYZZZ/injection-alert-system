from __future__ import annotations

import json

import pytest

from tests.e2e.pr7_block3bc_artifacts import (
    TimingSeries,
    build_run_metadata,
    write_run_metadata,
)


def test_timing_series_reports_bounded_distribution() -> None:
    series = TimingSeries("total_reconcile_ms")
    for value in (4.0, 2.0, 8.0, 6.0):
        series.add(value)
    result = series.summary()
    assert result["samples"] == 4
    assert result["min_ms"] == 2.0
    assert result["median_ms"] == 5.0
    assert result["max_ms"] == 8.0


def test_run_metadata_contains_only_bounded_safe_fields(tmp_path) -> None:
    series = TimingSeries("snapshot_fetch_ms")
    series.add(3.25)
    metadata = build_run_metadata(
        run_id="run_123",
        cybertrace_commit="a" * 40,
        portal_commit="b" * 40,
        model_version="locked-model",
        model_hashes={"weights": "c" * 64},
        image_digests={"waf": "waf@sha256:" + "d" * 64},
        commands=[{"command": "pytest", "exit_code": 0}],
        timings=[series],
        cleanup={"disabled": True, "effective_entries": 0, "leftovers": []},
    )
    output = tmp_path / "run.json"
    write_run_metadata(output, metadata)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "run_123"
    assert loaded["timings"][0]["samples"] == 1
    assert "token" not in output.read_text(encoding="utf-8").lower()


def test_timing_series_rejects_negative_values() -> None:
    series = TimingSeries("latency")
    with pytest.raises(ValueError, match="negative"):
        series.add(-1)
