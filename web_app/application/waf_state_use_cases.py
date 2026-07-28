from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.waf_state import canonical_state_checksum
from web_app.infrastructure.repositories.waf_state_repository import (
    WafSnapshot,
    WafStateRepository,
)

POLICY_VERSION = "confidence-waf-enforcement-v1"
SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_SCOPE = "RECORD_SEARCH"
MAX_SNAPSHOT_BYTES = 1024 * 1024


async def read_waf_snapshot(session: AsyncSession) -> dict[str, object]:
    snapshot: WafSnapshot = await WafStateRepository(session).snapshot()
    items = []
    for item in snapshot.items:
        expires_at = item["expires_at"]
        if not isinstance(expires_at, datetime):
            raise ValueError("snapshot expiry is not a datetime")
        expires_at = (
            expires_at.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        items.append({**item, "expires_at": expires_at})
    checksum = canonical_state_checksum(
        SNAPSHOT_SCHEMA_VERSION,
        POLICY_VERSION,
        snapshot.revision,
        SNAPSHOT_SCOPE,
        items,
    )
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "revision": snapshot.revision,
        "scope": SNAPSHOT_SCOPE,
        "generated_at": datetime.now(timezone.utc),
        "state_checksum_sha256": checksum,
        "items": items,
    }
