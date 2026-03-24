from datetime import datetime

import pytest
from pydantic import ValidationError

from web_app.presentation.schemas import WafIngestRequest


def test_accepts_minimal_valid_waf_event():
    payload = {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": "tx-123",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/login",
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }

    parsed = WafIngestRequest.model_validate(payload)

    assert parsed.transaction_id == "tx-123"
    assert isinstance(parsed.timestamp, datetime)
    assert parsed.timestamp.isoformat() == "2026-03-24T10:00:00+00:00"
    assert parsed.crs_rule_ids == ["942100"]
    assert parsed.crs_score == 8


def test_rejects_invalid_timestamp_format():
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-bad-ts",
                "timestamp": "not-a-timestamp",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )


def test_rejects_missing_transaction_id():
    """transaction_id is required for dedup."""
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )


def test_accepts_full_waf_event_with_optional_fields():
    payload = {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": "tx-456",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "POST",
        "request_path": "/api/login",
        "query_string": "user=admin",
        "request_headers": {"user-agent": "curl/8.0"},
        "sanitized_body": "' OR 1=1 --",
        "crs_score": 15,
        "crs_rule_ids": ["942100", "949110"],
        "matched_rule_messages": ["SQL Injection Attack Detected via libinjection"],
        "matched_rule_tags": ["attack-sqli", "paranoia-level/1"],
    }

    parsed = WafIngestRequest.model_validate(payload)

    assert parsed.query_string == "user=admin"
    assert parsed.request_headers == {"user-agent": "curl/8.0"}
    assert parsed.sanitized_body == "' OR 1=1 --"
    assert parsed.matched_rule_messages == [
        "SQL Injection Attack Detected via libinjection"
    ]
    assert parsed.matched_rule_tags == ["attack-sqli", "paranoia-level/1"]


def test_rejects_invalid_ingest_source():
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "unknown_source",
                "transaction_id": "tx-789",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": ["942100"],
            }
        )


def test_rejects_negative_crs_score():
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-neg",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": -1,
                "crs_rule_ids": ["942100"],
            }
        )


def test_rejects_empty_crs_rule_ids():
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-empty",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": [],
            }
        )


def test_rejects_sanitized_body_over_max_length():
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-long",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "POST",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": ["942100"],
                "sanitized_body": "x" * 1025,
            }
        )
