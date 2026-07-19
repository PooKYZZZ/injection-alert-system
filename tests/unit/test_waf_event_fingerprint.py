from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json

from web_app.application.waf_event_fingerprint import build_waf_event_fingerprint
from web_app.domain.source_address import SourceProvenance


def _event(**overrides):
    values = {
        "source_event_timestamp": datetime(
            2026, 3, 24, 10, 0, tzinfo=timezone.utc
        ),
        "source_ip": "203.0.113.10",
        "source_provenance": SourceProvenance.CLOUDFLARE_CONNECTING_IP,
        "cf_connecting_ip_matches_client_ip": True,
        "request_method": "post",
        "request_path": "/login",
        "query_string": "user=admin",
        "request_headers": {"User-Agent": " curl/8.0 ", "X-Test": " one "},
        "sanitized_body": "' OR 1=1 --",
        "crs_score": 8,
        "crs_rule_ids": ["949110", 942100, "942100"],
        "ingest_source": "modsec_audit_bridge",
        "matched_rule_messages": ["message-b", "message-a", "message-a"],
        "matched_rule_tags": ["tag-b", "tag-a", "tag-a"],
    }
    values.update(overrides)
    return values


def test_fingerprint_matches_locked_version_one_canonical_object() -> None:
    canonical = {
        "fingerprint_schema_version": 1,
        "source_event_timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "source_provenance": "CLOUDFLARE_CONNECTING_IP",
        "cf_connecting_ip_matches_client_ip": True,
        "request_method": "POST",
        "request_path": "/login",
        "query_string": "user=admin",
        "request_headers": {"user-agent": "curl/8.0", "x-test": "one"},
        "sanitized_body": "' OR 1=1 --",
        "crs_score": 8,
        "crs_rule_ids": ["942100", "949110"],
        "ingest_source": "modsec_audit_bridge",
        "matched_rule_messages": ["message-a", "message-b"],
        "matched_rule_tags": ["tag-a", "tag-b"],
    }
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    assert build_waf_event_fingerprint(**_event()) == hashlib.sha256(
        encoded
    ).hexdigest()


def test_fingerprint_is_stable_for_header_case_order_and_unordered_lists() -> None:
    first = build_waf_event_fingerprint(**_event())
    second = build_waf_event_fingerprint(
        **_event(
            request_headers={"x-test": "one", "user-agent": "curl/8.0"},
            crs_rule_ids=[942100, "949110"],
            matched_rule_messages=["message-a", "message-b"],
            matched_rule_tags=["tag-a", "tag-b"],
        )
    )

    assert first == second


def test_changing_one_factual_field_changes_fingerprint() -> None:
    assert build_waf_event_fingerprint(
        **_event()
    ) != build_waf_event_fingerprint(**_event(request_path="/different"))


def test_missing_source_timestamp_is_deterministic_null() -> None:
    first = build_waf_event_fingerprint(**_event(source_event_timestamp=None))
    second = build_waf_event_fingerprint(**_event(source_event_timestamp=None))

    assert first == second
    assert first == build_waf_event_fingerprint(**_event(source_event_timestamp=""))


def test_null_and_empty_query_strings_remain_distinct() -> None:
    assert build_waf_event_fingerprint(
        **_event(query_string=None)
    ) != build_waf_event_fingerprint(**_event(query_string=""))


def test_case_insensitive_header_collisions_retain_sorted_values() -> None:
    first = build_waf_event_fingerprint(
        **_event(request_headers={"Content-Type": " application/json ", "content-type": "text/plain"})
    )
    second = build_waf_event_fingerprint(
        **_event(request_headers={"content-type": "text/plain", "Content-Type": "application/json"})
    )

    assert first == second
    assert first != build_waf_event_fingerprint(
        **_event(request_headers={"Content-Type": "application/json", "content-type": "text/html"})
    )


def test_runtime_verification_conclusions_are_not_fingerprint_inputs() -> None:
    parameters = inspect.signature(build_waf_event_fingerprint).parameters

    assert "source_verification_status" not in parameters
    assert "verification_mode" not in parameters
    assert "transaction_id" not in parameters
