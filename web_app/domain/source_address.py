from __future__ import annotations

import ipaddress
from enum import StrEnum
from typing import Any


class SourceProvenance(StrEnum):
    CLOUDFLARE_CONNECTING_IP = "CLOUDFLARE_CONNECTING_IP"
    DIRECT_REMOTE_ADDR = "DIRECT_REMOTE_ADDR"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"


class SourceVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INVALID = "INVALID"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"


def canonicalize_source_ip(value: Any) -> str | None:
    if value is None:
        return None

    candidate = str(value).strip()
    if not candidate:
        return None

    if "," in candidate or "%" in candidate:
        return None

    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None

    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return str(address.ipv4_mapped)

    return str(address)
