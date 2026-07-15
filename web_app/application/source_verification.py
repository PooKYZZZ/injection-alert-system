from __future__ import annotations

from typing import Literal, TypeAlias

from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)

VerificationMode: TypeAlias = Literal[
    "unverified",
    "cloudflare_tunnel",
    "controlled_private_network",
]


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

    if mode == "controlled_private_network":
        if (
            provenance is SourceProvenance.DIRECT_REMOTE_ADDR
            and cf_connecting_ip_matches_client_ip is None
        ):
            return SourceVerificationStatus.VERIFIED
        return SourceVerificationStatus.UNVERIFIED

    return SourceVerificationStatus.UNVERIFIED
