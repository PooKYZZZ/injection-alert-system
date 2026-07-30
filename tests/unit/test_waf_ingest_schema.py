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
        "source_provenance": "DIRECT_REMOTE_ADDR",
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


def test_malformed_source_timestamp_becomes_null():
    parsed = WafIngestRequest.model_validate(
        {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": "tx-bad-ts",
            "timestamp": "not-a-timestamp",
            "source_ip": "203.0.113.10",
            "source_provenance": "DIRECT_REMOTE_ADDR",
            "request_method": "GET",
            "request_path": "/login",
            "crs_score": 8,
            "crs_rule_ids": ["942100"],
        }
    )

    assert parsed.timestamp is None


def test_naive_source_timestamp_is_rejected():
    with pytest.raises(ValidationError, match="explicit UTC offset"):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-naive-ts",
                "timestamp": "2026-03-24T10:00:00",
                "source_ip": "203.0.113.10",
                "source_provenance": "DIRECT_REMOTE_ADDR",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )


def test_offset_source_timestamp_is_normalized_to_utc():
    parsed = WafIngestRequest.model_validate(
        {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": "tx-offset-ts",
            "timestamp": "2026-03-24T18:00:00+08:00",
            "source_ip": "203.0.113.10",
            "source_provenance": "DIRECT_REMOTE_ADDR",
            "request_method": "GET",
            "request_path": "/login",
            "crs_score": 8,
            "crs_rule_ids": ["942100"],
        }
    )

    assert parsed.timestamp.isoformat() == "2026-03-24T10:00:00+00:00"


def test_rejects_missing_transaction_id():
    """transaction_id is required for dedup."""
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "source_provenance": "DIRECT_REMOTE_ADDR",
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
        "source_provenance": "CLOUDFLARE_CONNECTING_IP",
        "cf_connecting_ip_matches_client_ip": True,
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
                "source_provenance": "DIRECT_REMOTE_ADDR",
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
                "source_provenance": "DIRECT_REMOTE_ADDR",
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
                "source_provenance": "DIRECT_REMOTE_ADDR",
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
                "source_provenance": "DIRECT_REMOTE_ADDR",
                "request_method": "POST",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": ["942100"],
                "sanitized_body": "x" * 1025,
            }
        )


@pytest.mark.parametrize("source_ip", [None, "", "not-an-ip", "192.0.2.1:443"])
def test_missing_or_invalid_source_ip_becomes_null(source_ip) -> None:
    parsed = WafIngestRequest.model_validate(
        {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": "tx-invalid-source",
            "source_ip": source_ip,
            "source_provenance": "DIRECT_REMOTE_ADDR",
            "request_method": "GET",
            "request_path": "/login",
            "crs_score": 5,
            "crs_rule_ids": ["942100"],
        }
    )

    assert parsed.source_ip is None
    assert parsed.timestamp is None


def test_source_ip_is_canonicalized_at_request_boundary() -> None:
    parsed = WafIngestRequest.model_validate(
        {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": "tx-canonical-source",
            "source_ip": " ::ffff:192.0.2.128 ",
            "source_provenance": "DIRECT_REMOTE_ADDR",
            "request_method": "GET",
            "request_path": "/login",
            "crs_score": 5,
            "crs_rule_ids": ["942100"],
        }
    )

    assert parsed.source_ip == "192.0.2.128"


def test_rejects_legacy_unknown_provenance_in_live_request() -> None:
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-legacy",
                "source_ip": "203.0.113.10",
                "source_provenance": "LEGACY_UNKNOWN",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": ["942100"],
            }
        )


def test_rejects_direct_provenance_with_cloudflare_match_value() -> None:
    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(
            {
                "ingest_source": "modsec_audit_bridge",
                "transaction_id": "tx-invalid-direct-evidence",
                "source_ip": "203.0.113.10",
                "source_provenance": "DIRECT_REMOTE_ADDR",
                "cf_connecting_ip_matches_client_ip": False,
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 5,
                "crs_rule_ids": ["942100"],
            }
        )


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "source_verification_status",
        "source_trusted_for_enforcement",
        "unknown_field",
    ],
)
def test_rejects_client_supplied_or_unknown_fields(forbidden_field: str) -> None:
    payload = {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": "tx-forbidden-field",
        "source_ip": "203.0.113.10",
        "source_provenance": "DIRECT_REMOTE_ADDR",
        "request_method": "GET",
        "request_path": "/login",
        "crs_score": 5,
        "crs_rule_ids": ["942100"],
        forbidden_field: True,
    }

    with pytest.raises(ValidationError):
        WafIngestRequest.model_validate(payload)
