from __future__ import annotations

import pytest

from web_app.application.source_verification import (
    assign_server_source_provenance,
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


@pytest.mark.parametrize(
    "header, requested, match, expected",
    [
        (
            "authenticated",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            True,
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
        ),
        (
            None,
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            True,
            SourceProvenance.DIRECT_REMOTE_ADDR,
        ),
        (
            "modsecurity",
            SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            False,
            SourceProvenance.DIRECT_REMOTE_ADDR,
        ),
        (
            "modsecurity",
            SourceProvenance.DIRECT_REMOTE_ADDR,
            None,
            SourceProvenance.DIRECT_REMOTE_ADDR,
        ),
    ],
)
def test_server_assigns_cloudflare_provenance_only_from_marked_audit_evidence(
    header, requested, match, expected
) -> None:
    assert (
        assign_server_source_provenance(
            requested_provenance=requested,
            source_ip="203.0.113.7",
            cf_connecting_ip_matches_client_ip=match,
            mode="cloudflare_tunnel",
            audit_evidence_header=header,
        )
        is expected
    )


def test_caller_controlled_modsecurity_marker_is_not_authenticated() -> None:
    assert (
        assign_server_source_provenance(
            requested_provenance=SourceProvenance.CLOUDFLARE_CONNECTING_IP,
            source_ip="203.0.113.7",
            cf_connecting_ip_matches_client_ip=True,
            mode="cloudflare_tunnel",
            audit_evidence_header="modsecurity",
        )
        is SourceProvenance.DIRECT_REMOTE_ADDR
    )
