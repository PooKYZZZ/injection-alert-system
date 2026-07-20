"""
WAF Ingest Use Case — bridges validated WAF events to the existing triage flow.
"""

from __future__ import annotations

from datetime import datetime
import logging

from web_app.application.alert_events import IAlertEventPublisher
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
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)


class IShadowRecommendationRecorder:
    async def execute(
        self,
        *,
        alert_id: int | None,
        prediction: str,
        confidence_level: str,
        request_path: str,
    ) -> bool: ...


class WafIngestUseCase:
    """Thin wrapper that converts WAF events into the existing triage flow."""

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
        stale_processing_timeout_seconds: int = 30,
        enable_preprocessing: bool = True,
        source_verification_mode: VerificationMode = "unverified",
        alert_event_publisher: IAlertEventPublisher | None = None,
        recommendation_recorder: IShadowRecommendationRecorder | None = None,
    ):
        self._triage = TriageUseCase(
            classifier=classifier,
            repository=repository,
            stale_processing_timeout_seconds=stale_processing_timeout_seconds,
            enable_preprocessing=enable_preprocessing,
            alert_event_publisher=alert_event_publisher,
        )
        self._source_verification_mode = source_verification_mode
        self._recommendation_recorder = recommendation_recorder

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
        ):
            log_event(
                logger,
                "source_provenance_mode_mismatch",
                "WAF source provenance does not match verification mode",
                level="WARNING",
                transaction_id=transaction_id,
                verification_mode=self._source_verification_mode,
                source_provenance=source_provenance.value,
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

        result = await self._triage.ingest(command)
        if self._recommendation_recorder is not None and result.alert_id is not None:
            try:
                await self._recommendation_recorder.execute(
                    alert_id=result.alert_id,
                    prediction=result.prediction,
                    confidence_level=result.confidence_level,
                    request_path=request_path,
                )
            except Exception as exc:  # shadow recording must not affect ingest
                log_event(
                    logger,
                    "enforcement.shadow_recommendation_failed",
                    "Shadow recommendation failed after triage; ingest result is unchanged",
                    level="WARNING",
                    transaction_id=transaction_id,
                    error_type=type(exc).__name__,
                )
        return result
