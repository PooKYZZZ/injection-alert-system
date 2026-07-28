from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping


class WafLifecycle(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


def canonicalize_waf_source_ip(value: Any) -> str | None:
    if value is None:
        return None
    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return str(address.ipv4_mapped)
    return str(address)


def utc_millis(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("UTC-aware datetime required")
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def transition_status(current: WafLifecycle, target: WafLifecycle) -> bool:
    if current is WafLifecycle.ACTIVE and target in {
        WafLifecycle.SUPERSEDED,
        WafLifecycle.REVOKED,
        WafLifecycle.EXPIRED,
    }:
        return True
    raise ValueError(f"invalid WAF lifecycle transition: {current} -> {target}")


def _expiry_key(value: str) -> int:
    if not value.endswith("Z"):
        raise ValueError("UTC-aware datetime required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    return utc_millis(parsed)


def canonical_state_checksum(
    schema_version: int,
    policy_version: str,
    revision: int,
    scope: str,
    items: list[Mapping[str, Any]],
) -> str:
    normalized = [dict(item) for item in items]
    normalized.sort(
        key=lambda item: (
            ipaddress.ip_address(item["source_ip"]).version,
            ipaddress.ip_address(item["source_ip"]).packed,
            item["request_path"],
            _expiry_key(item["expires_at"]),
            item["recommendation_id"],
            item["entry_id"],
        )
    )
    state = {
        "schema_version": schema_version,
        "policy_version": policy_version,
        "revision": revision,
        "scope": scope,
        "items": normalized,
    }
    payload = json.dumps(
        state,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()
