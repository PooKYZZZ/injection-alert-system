from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from web_app.domain.source_address import (
    SourceProvenance,
    canonicalize_source_ip,
)


def _normalize_source_timestamp(value: datetime | str | None) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    normalized = parsed.astimezone(timezone.utc).isoformat()
    return normalized.replace("+00:00", "Z")


def _canonical_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    canonical: dict[str, str] = {}
    items = sorted(
        (headers or {}).items(),
        key=lambda item: (str(item[0]).strip().lower(), str(item[0])),
    )
    for key, value in items:
        canonical[str(key).strip().lower()] = str(value).strip()
    return canonical


def _sorted_unique_strings(values: list[Any] | None) -> list[str]:
    return sorted({str(value) for value in values or []})


def build_waf_event_fingerprint(
    *,
    source_event_timestamp: datetime | str | None,
    source_ip: str | None,
    source_provenance: SourceProvenance,
    cf_connecting_ip_matches_client_ip: bool | None,
    request_method: str,
    request_path: str,
    query_string: str | None,
    request_headers: dict[str, Any] | None,
    sanitized_body: str | None,
    crs_score: int,
    crs_rule_ids: list[Any],
    ingest_source: str,
    matched_rule_messages: list[Any] | None,
    matched_rule_tags: list[Any] | None,
) -> str:
    canonical_event = {
        "fingerprint_schema_version": 1,
        "source_event_timestamp": _normalize_source_timestamp(
            source_event_timestamp
        ),
        "source_ip": canonicalize_source_ip(source_ip),
        "source_provenance": source_provenance.value,
        "cf_connecting_ip_matches_client_ip": (
            cf_connecting_ip_matches_client_ip
        ),
        "request_method": request_method.upper(),
        "request_path": request_path,
        "query_string": query_string,
        "request_headers": _canonical_headers(request_headers),
        "sanitized_body": sanitized_body,
        "crs_score": crs_score,
        "crs_rule_ids": _sorted_unique_strings(crs_rule_ids),
        "ingest_source": ingest_source,
        "matched_rule_messages": _sorted_unique_strings(
            matched_rule_messages
        ),
        "matched_rule_tags": _sorted_unique_strings(matched_rule_tags),
    }
    encoded = json.dumps(
        canonical_event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
