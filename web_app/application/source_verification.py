from __future__ import annotations

from typing import Literal, TypeAlias

from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)

VerificationMode: TypeAlias = Literal[
    "unverified",
    "cloudflare_tunnel",
]

WAF_AUDIT_EVIDENCE_HEADER = "X-CyberTrace-WAF-Audit"


def assign_server_source_provenance(
    *,
    requested_provenance: SourceProvenance,
    source_ip: str | None,
    cf_connecting_ip_matches_client_ip: bool | None,
    mode: VerificationMode,
    audit_evidence_header: str | None,
) -> SourceProvenance:
    """Assign trusted provenance only for marked ModSecurity audit evidence."""
    if (
        mode == "cloudflare_tunnel"
        and requested_provenance is SourceProvenance.CLOUDFLARE_CONNECTING_IP
        and source_ip is not None
        and cf_connecting_ip_matches_client_ip is True
        and audit_evidence_header == "modsecurity"
    ):
        return SourceProvenance.CLOUDFLARE_CONNECTING_IP
    return SourceProvenance.DIRECT_REMOTE_ADDR


def derive_source_verification_status(
    *,
    source_ip: str | None,
    provenance: SourceProvenance,
    cf_connecting_ip_matches_client_ip: bool | None,
    mode: VerificationMode,
) -> SourceVerificationStatus:
    if source_ip is None:
        return SourceVerificationStatus.INVALID

    if mode == "cloudflare_tunnel":
        if (
            provenance is SourceProvenance.CLOUDFLARE_CONNECTING_IP
            and cf_connecting_ip_matches_client_ip is True
        ):
            return SourceVerificationStatus.VERIFIED
        return SourceVerificationStatus.UNVERIFIED

    return SourceVerificationStatus.UNVERIFIED
