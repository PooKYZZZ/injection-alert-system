import json

import scripts.measure_shadow_enforcement_latency as measure


def test_percentile_is_deterministic():
    assert measure.percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
    assert measure.percentile([1.0, 2.0, 3.0, 4.0], 95) == 3.85


def test_measure_counts_success_timeout_and_error(monkeypatch):
    outcomes = ["success", "timeout", "error", "success"]
    monkeypatch.setattr(measure, "_request_once", lambda url, timeout: outcomes.pop(0))
    ticks = iter([0.000, 0.002, 0.010, 0.011, 0.020, 0.025, 0.030, 0.034])
    result = measure.measure_samples(
        "http://portal.test", "/records/search", count=4, timeout=1.0,
        clock=lambda: next(ticks),
    )
    assert result["samples"] == 4
    assert result["successes"] == 2
    assert result["timeouts"] == 1
    assert result["errors"] == 1
    assert result["p50_ms"] == 3.0


def test_main_json_output_omits_query_values(monkeypatch, capsys):
    monkeypatch.setattr(
        measure,
        "measure_samples",
        lambda *args, **kwargs: {
            "samples": 1,
            "successes": 1,
            "errors": 0,
            "timeouts": 0,
            "p50_ms": 2.0,
            "p95_ms": 2.0,
            "p99_ms": 2.0,
            "max_ms": 2.0,
        },
    )
    assert measure.main(
        [
            "--base-url",
            "http://portal.test",
            "--route",
            "/records/search?query=secret-value",
            "--count",
            "1",
            "--json",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "secret-value" not in output
    assert json.loads(output)["route"] == "/records/search"


def test_main_returns_nonzero_when_no_samples(monkeypatch):
    monkeypatch.setattr(
        measure,
        "measure_samples",
        lambda *args, **kwargs: {
            "samples": 2,
            "successes": 0,
            "errors": 2,
            "timeouts": 0,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
        },
    )
    assert measure.main(["--base-url", "http://portal.test", "--count", "2"]) == 1
