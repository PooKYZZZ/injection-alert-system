from __future__ import annotations

import hashlib
import ipaddress
from dataclasses import dataclass

from .snapshot import MAX_ITEMS, PATH, Snapshot, _timestamp_epoch

RULE_ID_START = 10000


@dataclass(frozen=True)
class RenderedCandidate:
    content: str
    checksum_sha256: str
    revision: int
    entry_count: int


def render_candidate(
    revision: int, items: list[dict] | tuple[dict, ...]
) -> RenderedCandidate:
    if len(items) > MAX_ITEMS:
        raise ValueError("candidate item limit exceeded: 512")
    ordered = sorted(
        items,
        key=lambda item: (
            ipaddress.ip_address(item["source_ip"]).version,
            ipaddress.ip_address(item["source_ip"]).packed,
            item["request_path"],
            _timestamp_epoch(item["expires_at"]),
            item["recommendation_id"],
            item["entry_id"],
        ),
    )
    lines = ["# PR7 dynamic WAF candidate"]
    for offset, item in enumerate(ordered):
        rule_id = RULE_ID_START + offset
        expiry = _timestamp_epoch(item["expires_at"]) // 1000 - 1
        source = item["source_ip"]
        recommendation = item["recommendation_id"]
        action = (
            f'chain,id:{rule_id},phase:1,deny,log,status:403,t:none,'
            f"msg:'PR7 WAF block',"
            f"tag:'pr7',tag:'revision-{revision}',tag:'recommendation-{recommendation}'"
        )
        lines.append(
            f'SecRule REQUEST_FILENAME "@streq {PATH}" "{action}"'
        )
        lines.append(f'    SecRule REMOTE_ADDR "@ipMatch {source}" "chain,t:none"')
        lines.append(f'    SecRule TIME_EPOCH "@lt {expiry}" "t:none"')
    content = "\n".join(lines) + "\n"
    encoded = content.encode("ascii")
    return RenderedCandidate(
        content, hashlib.sha256(encoded).hexdigest(), revision, len(ordered)
    )


def render_snapshot(snapshot: Snapshot) -> RenderedCandidate:
    return render_candidate(snapshot.revision, snapshot.items)
