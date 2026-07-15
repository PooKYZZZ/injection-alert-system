from __future__ import annotations

import pytest

from web_app.application.source_verification import (
    derive_source_verification_status,
)
from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)


@pytest.mark.parametrize(
    (
        "source_ip",
        "provenance",
        "matches",
        "mode",
        "expected",
    ),
    [
        (
            None,
            SourceProvenance.DIRECT_REMOTE_ADDR,
            None,
            "unverified",
            SourceVerificationStatus.INVALID,
        ),
        (
            "203.0.113.10",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            True,
            "cloudflare_tunnel",
            SourceVerificationStatus.VERIFIED,
        ),
        (
            "203.0.113.10",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            False,
            "cloudflare_tunnel",
            SourceVerificationStatus.UNVERIFIED,
        ),
        (
            "203.0.113.10",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            None,
            "cloudflare_tunnel",
            SourceVerificationStatus.UNVERIFIED,
        ),
        (
            "203.0.113.10",
            SourceProvenance.DIRECT_REMOTE_ADDR,
            None,
            "unverified",
            SourceVerificationStatus.UNVERIFIED,
        ),
        (
            "203.0.113.10",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            True,
            "unverified",
            SourceVerificationStatus.UNVERIFIED,
        ),
    ],
)
def test_derive_source_verification_status(
    source_ip: str | None,
    provenance: SourceProvenance,
    matches: bool | None,
    mode: str,
    expected: SourceVerificationStatus,
) -> None:
    assert (
        derive_source_verification_status(
            source_ip=source_ip,
            provenance=provenance,
            cf_connecting_ip_matches_client_ip=matches,
            mode=mode,
        )
        is expected
    )
