from __future__ import annotations

import pytest

import scripts.search_route_attack_tester as tester
from scripts.search_route_attack_tester import (
    _expected_action,
    _request_uri_matches,
    _validate_endpoint,
    build_reference_bundle,
)


def test_endpoint_validation_allows_only_local_origins() -> None:
    assert (
        _validate_endpoint(
            "http://demo-target-modsecurity:8080",
            allowed_hosts={"demo-target-modsecurity"},
            label="origin",
        )
        == "http://demo-target-modsecurity:8080"
    )
    with pytest.raises(ValueError, match="local HTTP origin"):
        _validate_endpoint(
            "https://example.invalid:443",
            allowed_hosts={"demo-target-modsecurity"},
            label="origin",
        )
    with pytest.raises(ValueError, match="local HTTP origin"):
        _validate_endpoint(
            "http://demo-target-modsecurity:8080/dashboard",
            allowed_hosts={"demo-target-modsecurity"},
            label="origin",
        )


def test_expected_action_uses_existing_policy() -> None:
    assert _expected_action("Normal", "CRITICAL") == "ALLOWED"
    assert _expected_action("SQL Injection", "LOW") == "ALLOWED"
    assert _expected_action("Code Injection", "MEDIUM") == "THROTTLED"
    assert _expected_action("Other Attacks", "HIGH") == "BLOCKED"
    assert _expected_action("Other Attacks", "CRITICAL") == "BLOCKED"


def test_audit_match_requires_search_records_uri() -> None:
    event = {
        "transaction": {
            "request": {"uri": "/records/search?query=one%27+OR+1%3D1"},
        }
    }
    case = {
        "request_uri": "/records/search?query=one%27+OR+1%3D1",
    }
    assert _request_uri_matches(event, case)
    assert not _request_uri_matches(
        event,
        {"request_uri": "/dashboard?query=one%27+OR+1%3D1"},
    )


def _row(
    *,
    family: str,
    case_id: str,
    expected_label: str,
    predicted_label: str,
    confidence: str,
    confidence_level: str,
    classification_correct: str,
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "seed_id": f"{case_id}-seed",
        "family": family,
        "variant": "seed",
        "mutation": "seed_identity",
        "payload": "safe-test-value",
        "wire_query": "safe-test-value",
        "payload_sha256": "payload-hash",
        "wire_sha256": "wire-hash",
        "expected_label": expected_label,
        "predicted_label": predicted_label,
        "classification_correct": classification_correct,
        "confidence": confidence,
        "confidence_level": confidence_level,
        "expected_action": "BLOCKED",
        "action_taken": "BLOCKED",
        "action_match": "True",
        "http_status": "403",
        "waf_status": "BLOCKED",
        "transaction_id": "tx-test",
        "backend_alert_id": "1",
        "acceptance_status": "PASS",
    }


def test_reference_bundle_keeps_exact_class_and_confidence_fields() -> None:
    rows = [
        _row(
            family="sql_injection",
            case_id="SR-SQL-001",
            expected_label="SQL Injection",
            predicted_label="SQL Injection",
            confidence="0.990000",
            confidence_level="CRITICAL",
            classification_correct="True",
        ),
        _row(
            family="code_injection",
            case_id="SR-CODE-001",
            expected_label="Code Injection",
            predicted_label="Code Injection",
            confidence="0.600000",
            confidence_level="MEDIUM",
            classification_correct="True",
        ),
        _row(
            family="general_attack",
            case_id="SR-GEN-001",
            expected_label="Other Attacks",
            predicted_label="Code Injection",
            confidence="0.700000",
            confidence_level="MEDIUM",
            classification_correct="False",
        ),
    ]
    bundle = build_reference_bundle(rows, run_id="search-records-test")
    assert bundle["confirmed_sql_injection_examples"][0]["case_id"] == "SR-SQL-001"
    assert bundle["confirmed_code_injection_examples"][0]["confidence"] == "0.600000"
    medium = bundle["known_medium_confidence_general_attack_cases"]
    assert medium[0]["case_id"] == "SR-GEN-001"
    assert medium[0]["classification_correct"] == "False"


def test_reference_rows_do_not_require_a_raw_http_request_field() -> None:
    rows = [
        _row(
            family="general_attack",
            case_id="SR-GEN-001",
            expected_label="Other Attacks",
            predicted_label="Other Attacks",
            confidence="0.800000",
            confidence_level="HIGH",
            classification_correct="True",
        )
    ]
    bundle = build_reference_bundle(rows, run_id="search-records-test")
    assert "http_request" not in bundle["confirmed_general_attack_examples"][0]


def test_backend_lookup_waits_for_processing_row_to_complete(monkeypatch) -> None:
    responses = iter(
        [
            ({"found": True, "status": "PROCESSING"}, None),
            (
                {
                    "found": True,
                    "status": "COMPLETED",
                    "prediction": "SQL Injection",
                    "confidence": 0.99,
                    "confidence_level": "CRITICAL",
                    "action_taken": "BLOCKED",
                },
                None,
            ),
        ]
    )
    sleeps: list[float] = []

    monkeypatch.setattr(
        tester, "_backend_lookup", lambda *args, **kwargs: next(responses)
    )
    monkeypatch.setattr(tester.time, "sleep", sleeps.append)

    payload, error = tester._poll_backend(
        opener=object(),
        backend="http://127.0.0.1:8000",
        transaction_id="tx-processing",
        api_key="",
        timeout_seconds=1.0,
    )

    assert error is None
    assert payload is not None
    assert payload["status"] == "COMPLETED"
    assert sleeps == [0.15]
