"""
WAF Ingest Use Case — bridges validated WAF events to the existing triage flow.
"""

from __future__ import annotations

from datetime import datetime

from web_app.application.source_verification import (
    VerificationMode,
    derive_source_verification_status,
)
from web_app.application.triage_use_case import (
    IClassifier,
    TriageIngestCommand,
    TriageResult,
    TriageUseCase,
)
from web_app.application.waf_event_sanitizer import sanitize_waf_event
from web_app.application.waf_event_fingerprint import build_waf_event_fingerprint
from web_app.domain.interfaces import ITrafficLogRepository
from web_app.domain.source_address import (
    SourceProvenance,
    canonicalize_source_ip,
)


class SourceProvenanceModeError(ValueError):
    """Raised when a verifying runtime receives evidence from another topology."""


class WafIngestUseCase:
    """Thin wrapper that converts WAF events into the existing triage flow."""

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
        stale_processing_timeout_seconds: int = 30,
        enable_preprocessing: bool = True,
        source_verification_mode: VerificationMode = "unverified",
    ):
        self._triage = TriageUseCase(
            classifier=classifier,
            repository=repository,
            stale_processing_timeout_seconds=stale_processing_timeout_seconds,
            enable_preprocessing=enable_preprocessing,
        )
        self._source_verification_mode = source_verification_mode

    async def execute(
        self,
        *,
        transaction_id: str,
        timestamp: datetime | None,
        ingest_source: str = "modsec_audit_bridge",
        source_ip: str | None,
        source_provenance: SourceProvenance = SourceProvenance.DIRECT_REMOTE_ADDR,
        cf_connecting_ip_matches_client_ip: bool | None = None,
        request_method: str,
        request_path: str,
        request_headers: dict[str, str] | None = None,
        sanitized_body: str | None = None,
        crs_score: int,
        crs_rule_ids: list[str],
        query_string: str | None = None,
        matched_rule_messages: list[str] | None = None,
        matched_rule_tags: list[str] | None = None,
    ) -> TriageResult:
        if (
            self._source_verification_mode == "cloudflare_tunnel"
            and source_provenance is not SourceProvenance.CLOUDFLARE_CONNECTING_IP
        ) or (
            self._source_verification_mode == "controlled_private_network"
            and source_provenance is not SourceProvenance.DIRECT_REMOTE_ADDR
        ):
            raise SourceProvenanceModeError(
                "Source provenance is incompatible with the active verification mode"
            )

        source_ip = canonicalize_source_ip(source_ip)
        uri = request_path
        if query_string:
            uri = f"{request_path}?{query_string}"
        http_request = f"{request_method} {uri} HTTP/1.1"

        sanitized_headers: dict[str, str] = {}
        canonical_body = sanitized_body
        if request_headers or sanitized_body:
            sanitized = sanitize_waf_event(
                {
                    "request_headers": request_headers or {},
                    "sanitized_body": sanitized_body,
                }
            )
            sanitized_headers = sanitized.get("request_headers") or {}
            canonical_body = sanitized.get("sanitized_body")

        source_verification_status = derive_source_verification_status(
            source_ip=source_ip,
            provenance=source_provenance,
            cf_connecting_ip_matches_client_ip=(
                cf_connecting_ip_matches_client_ip
            ),
            mode=self._source_verification_mode,
        )
        ingest_fingerprint_sha256 = build_waf_event_fingerprint(
            source_event_timestamp=timestamp,
            source_ip=source_ip,
            source_provenance=source_provenance,
            cf_connecting_ip_matches_client_ip=(
                cf_connecting_ip_matches_client_ip
            ),
            request_method=request_method,
            request_path=request_path,
            query_string=query_string,
            request_headers=sanitized_headers,
            sanitized_body=canonical_body,
            crs_score=crs_score,
            crs_rule_ids=crs_rule_ids,
            ingest_source=ingest_source,
            matched_rule_messages=matched_rule_messages,
            matched_rule_tags=matched_rule_tags,
        )

        command = TriageIngestCommand(
            transaction_id=transaction_id,
            timestamp=timestamp,
            source_ip=source_ip,
            request_method=request_method,
            request_uri=request_path,
            request_headers=sanitized_headers,
            request_body=canonical_body or "",
            http_request=http_request,
            crs_score=crs_score,
            crs_rule_ids=crs_rule_ids,
            ingest_source=ingest_source,
            matched_rule_messages=matched_rule_messages,
            matched_rule_tags=matched_rule_tags,
            query_string=query_string,
            source_provenance=source_provenance,
            source_verification_status=source_verification_status,
            ingest_fingerprint_sha256=ingest_fingerprint_sha256,
        )

        return await self._triage.ingest(command)
