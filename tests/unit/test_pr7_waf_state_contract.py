from datetime import datetime, timezone

import pytest

from web_app.domain.waf_state import (
    PR7_PATH,
    PR7_POLICY_VERSION,
    PR7_SCOPE,
    WafLifecycle,
    canonical_state_checksum,
    canonicalize_waf_source_ip,
    transition_status,
    utc_millis,
    utc_millis_string,
)


def test_waf_ip_canonicalization_collapses_mapped_ipv6() -> None:
    assert canonicalize_waf_source_ip("::ffff:203.0.113.7") == "203.0.113.7"
    assert canonicalize_waf_source_ip("2001:0db8::1") == "2001:db8::1"
    assert canonicalize_waf_source_ip("not-an-ip") is None


def test_utc_millis_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="UTC-aware datetime required"):
        utc_millis(datetime(2026, 7, 28, 0, 0, 0))
    with pytest.raises(ValueError, match="UTC-aware datetime required"):
        utc_millis_string(datetime(2026, 7, 28, 0, 0, 0))
    assert utc_millis(datetime(2026, 7, 28, tzinfo=timezone.utc)) == 1785196800000
    assert (
        utc_millis_string(datetime(2026, 7, 28, 0, 0, 0, 123456, timezone.utc))
        == "2026-07-28T00:00:00.123Z"
    )


def test_pr7_policy_constants_are_fixed() -> None:
    assert PR7_SCOPE == "RECORD_SEARCH"
    assert PR7_PATH == "/records/search"
    assert PR7_POLICY_VERSION == "confidence-waf-enforcement-v1"


def test_lifecycle_only_allows_active_terminal_transitions() -> None:
    assert transition_status(WafLifecycle.ACTIVE, WafLifecycle.EXPIRED)
    with pytest.raises(ValueError):
        transition_status(WafLifecycle.EXPIRED, WafLifecycle.ACTIVE)


def test_checksum_ignores_generated_at_and_input_order() -> None:
    items = [
        {
            "entry_id": 2,
            "recommendation_id": 8,
            "source_ip": "203.0.113.8",
            "request_path": "/b",
            "expires_at": "2026-07-28T00:00:02.000Z",
        },
        {
            "entry_id": 1,
            "recommendation_id": 7,
            "source_ip": "203.0.113.7",
            "request_path": "/a",
            "expires_at": "2026-07-28T00:00:01.000Z",
        },
    ]
    first = canonical_state_checksum(
        1, "confidence-waf-enforcement-v1", 1, "RECORD_SEARCH", items
    )
    second = canonical_state_checksum(
        1, "confidence-waf-enforcement-v1", 1, "RECORD_SEARCH", list(reversed(items))
    )
    assert first == second
