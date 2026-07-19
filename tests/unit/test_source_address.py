from __future__ import annotations

import pytest

from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
    canonicalize_source_ip,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.0.2.1", "192.0.2.1"),
        ("2001:0DB8:0000:0000:0000:0000:0000:0001", "2001:db8::1"),
        ("2001:db8::1", "2001:db8::1"),
        ("::ffff:192.0.2.128", "192.0.2.128"),
        ("::ffff:c000:0280", "192.0.2.128"),
        ("  198.51.100.7\t", "198.51.100.7"),
        (None, None),
        ("", None),
        ("   ", None),
        ("192.0.2.1, 198.51.100.7", None),
        ("192.0.2.1:443", None),
        ("[2001:db8::1]:443", None),
        ("fe80::1%eth0", None),
        ("not-an-address", None),
    ],
)
def test_canonicalize_source_ip(value: object, expected: str | None) -> None:
    assert canonicalize_source_ip(value) == expected


def test_source_metadata_enum_values_are_stable() -> None:
    assert {member.value for member in SourceProvenance} == {
        "CLOUDFLARE_CONNECTING_IP",
        "DIRECT_REMOTE_ADDR",
        "LEGACY_UNKNOWN",
    }
    assert {member.value for member in SourceVerificationStatus} == {
        "VERIFIED",
        "UNVERIFIED",
        "INVALID",
        "LEGACY_UNKNOWN",
    }
