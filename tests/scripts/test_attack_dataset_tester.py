import csv
import io
import json
from pathlib import Path

import pytest

from scripts.attack_dataset_tester import (
    REPORT_FIELDS,
    AttackSample,
    PredictionResult,
    _report_row,
    acceptance_status,
    choose_samples,
    classify_failure,
    expected_action_for,
    normalize_samples,
    validate_endpoint,
    write_evidence_csv,
)


def _sample(**overrides):
    values = {
        "row_id": "case-1",
        "label": "SQL Injection",
        "http_request": "GET /search?q=fixture HTTP/1.1\nHost: localhost",
        "case_id": "SQL-001",
        "source_fixture_id": "fixture-sqli-001",
        "family": "sql_injection",
        "ground_truth_status": "approved_fixture",
        "expected_waf": "BLOCK_IF_CRS_MATCHES",
        "replay_policy": "offline_only",
        "catalog_version": "panelist-local-v1",
    }
    values.update(overrides)
    return AttackSample(**values)


def _result(sample=None, **overrides):
    values = {
        "sample": sample or _sample(),
        "ok": True,
        "status_code": 200,
        "duration_ms": 4.2,
        "predicted_label": "SQL Injection",
        "confidence": 0.95,
        "confidence_level": "CRITICAL",
        "action_taken": "BLOCKED",
        "error": None,
        "raw_body": '{"class_label":"SQL Injection"}',
    }
    values.update(overrides)
    return PredictionResult(**values)


def test_normalize_samples_keeps_panel_metadata():
    samples = normalize_samples(
        [
            {
                "catalog_version": "panelist-local-v1",
                "case_id": "SQL-001",
                "case_version": 2,
                "source_fixture_id": "fixture-sqli-001",
                "family": "sql_injection",
                "variant": "identity",
                "description": "known fixture",
                "ground_truth_status": "approved_fixture",
                "expected_waf": "BLOCK_IF_CRS_MATCHES",
                "replay_policy": "offline_only",
                "selection_tags": ["positive_control"],
                "expected_label": "SQL Injection",
                "combined_payload": "GET /search?q=fixture HTTP/1.1\nHost: localhost",
            }
        ],
        include_labels={"SQL Injection"},
        include_normal=False,
    )

    assert len(samples) == 1
    assert samples[0].case_id == "SQL-001"
    assert samples[0].case_version == 2
    assert samples[0].selection_tags == ("positive_control",)


def test_choose_samples_caps_zero_limit_at_safe_batch_maximum():
    samples = [
        _sample(row_id=f"case-{index}", case_id=f"case-{index}") for index in range(125)
    ]

    selected = choose_samples(samples, limit=0, seed=20260902)

    assert len(selected) == 100


def test_endpoint_rejects_public_destination_by_default():
    with pytest.raises(ValueError, match="non-local endpoint"):
        validate_endpoint("https://example.invalid/api/predict", allow_nonlocal=False)


@pytest.mark.parametrize(
    ("label", "tier", "action"),
    [
        ("Normal", "CRITICAL", "ALLOWED"),
        ("SQL Injection", "LOW", "ALLOWED"),
        ("SQL Injection", "MEDIUM", "THROTTLED"),
        ("SQL Injection", "HIGH", "BLOCKED"),
        ("SQL Injection", "CRITICAL", "BLOCKED"),
        ("Other Attacks", "CRITICAL", None),
    ],
)
def test_expected_action_uses_existing_policy(label, tier, action):
    assert expected_action_for(label, tier) == action


def test_report_contains_required_fields_without_raw_request():
    result = _result()
    row = _report_row(
        result,
        run_id="attack-test-run",
        observed_at_utc="2026-09-02T00:00:00Z",
        environment="local-offline",
        endpoint="http://127.0.0.1:8000/api/predict",
        metadata={
            "model_version": "model-v1",
            "model_digest": "d" * 64,
            "checkpoint_digest": "c" * 64,
            "preprocessing_version": "model-input-v2-redacted",
            "model_temperature": 0.596868,
            "threshold_low": "0.50",
            "threshold_high": "0.80",
            "threshold_critical": "0.90",
        },
    )

    assert set(REPORT_FIELDS) == set(row)
    assert row["input_sha256"]
    assert row["acceptance_status"] == "PASS"
    assert "http_request" not in row
    assert "fixture" not in json.dumps(row["input_sha256"])


def test_out_of_scope_result_requires_no_action():
    sample = _sample(label="Other Attacks", family="other_attacks")
    result = _result(
        sample=sample,
        predicted_label="Other Attacks",
        action_taken=None,
    )

    assert classify_failure(result) == ""
    assert acceptance_status(result) == "PASS"
    row = _report_row(
        result,
        run_id="attack-test-run",
        observed_at_utc="2026-09-02T00:00:00Z",
        environment="local-offline",
        endpoint="http://127.0.0.1:8000/api/predict",
        metadata={},
    )
    assert row["expected_action"] == ""
    assert row["action_taken"] == ""
    assert row["action_match"] == "True"


def test_proposed_variant_is_review_even_when_prediction_matches():
    result = _result(
        sample=_sample(ground_truth_status="proposed_semantics_preserving")
    )

    assert acceptance_status(result) == "REVIEW"


def test_approved_mismatch_is_ml_label_failure():
    result = _result(predicted_label="Other Attacks", confidence_level="CRITICAL")

    assert classify_failure(result) == "ml_label"
    assert acceptance_status(result) == "FAIL"


def test_csv_writer_emits_all_columns(tmp_path: Path):
    row = _report_row(
        _result(),
        run_id="attack-test-run",
        observed_at_utc="2026-09-02T00:00:00Z",
        environment="local-offline",
        endpoint="http://127.0.0.1:8000/api/predict",
        metadata={},
    )
    output = tmp_path / "report.csv"

    write_evidence_csv([row], output)

    with output.open(newline="", encoding="utf-8") as handle:
        parsed = list(csv.DictReader(io.StringIO(handle.read())))
    assert parsed[0]["case_id"] == "SQL-001"
    assert set(parsed[0]) == set(REPORT_FIELDS)
