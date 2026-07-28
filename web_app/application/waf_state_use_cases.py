from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.waf_state import (
    PR7_MAX_ENTRIES,
    PR7_PATH,
    PR7_POLICY_VERSION,
    PR7_SCOPE,
    canonical_state_checksum,
    canonicalize_waf_source_ip,
    utc_millis_string,
)
from web_app.infrastructure.repositories.waf_state_repository import (
    WafSnapshot,
    WafStateRepository,
)

POLICY_VERSION = "confidence-waf-enforcement-v1"
SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_SCOPE = PR7_SCOPE
MAX_SNAPSHOT_BYTES = 1024 * 1024


async def read_waf_snapshot(session: AsyncSession) -> dict[str, object]:
    snapshot: WafSnapshot = await WafStateRepository(session).snapshot()
    if len(snapshot.items) > PR7_MAX_ENTRIES:
        raise ValueError("snapshot entry limit exceeded")
    items = []
    entry_ids: set[int] = set()
    recommendation_ids: set[int] = set()
    source_paths: set[tuple[str, str]] = set()
    for item in snapshot.items:
        entry_id = item.get("entry_id")
        recommendation_id = item.get("recommendation_id")
        source_ip = item.get("source_ip")
        request_path = item.get("request_path")
        expires_at = item["expires_at"]
        if not isinstance(entry_id, int) or entry_id < 1:
            raise ValueError("invalid snapshot entry identity")
        if not isinstance(recommendation_id, int) or recommendation_id < 1:
            raise ValueError("invalid snapshot recommendation identity")
        if entry_id in entry_ids or recommendation_id in recommendation_ids:
            raise ValueError("duplicate snapshot identity")
        if not isinstance(source_ip, str):
            raise ValueError("snapshot source IP is not a string")
        if canonicalize_waf_source_ip(source_ip) != source_ip:
            raise ValueError("snapshot source IP is not canonical")
        if not isinstance(request_path, str) or request_path != PR7_PATH:
            raise ValueError("snapshot path is not approved")
        if (source_ip, request_path) in source_paths:
            raise ValueError("duplicate snapshot source/path")
        if not isinstance(expires_at, datetime):
            raise ValueError("snapshot expiry is not a datetime")
        entry_ids.add(entry_id)
        recommendation_ids.add(recommendation_id)
        source_paths.add((source_ip, request_path))
        items.append(
            {
                "entry_id": entry_id,
                "recommendation_id": recommendation_id,
                "source_ip": source_ip,
                "request_path": request_path,
                "expires_at": utc_millis_string(expires_at),
            }
        )
    checksum = canonical_state_checksum(
        SNAPSHOT_SCHEMA_VERSION,
        PR7_POLICY_VERSION,
        snapshot.revision,
        SNAPSHOT_SCOPE,
        items,
    )
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "policy_version": PR7_POLICY_VERSION,
        "revision": snapshot.revision,
        "scope": SNAPSHOT_SCOPE,
        "generated_at": utc_millis_string(datetime.now(timezone.utc)),
        "state_checksum_sha256": checksum,
        "items": items,
    }
