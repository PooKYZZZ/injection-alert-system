"""
WAF Ingest Use Case — bridges validated WAF events to the existing triage flow.
"""

from __future__ import annotations

from datetime import datetime

from web_app.application.triage_use_case import (
    IClassifier,
    TriageIngestCommand,
    TriageResult,
    TriageUseCase,
)
from web_app.application.waf_event_sanitizer import sanitize_waf_event
from web_app.domain.interfaces import ITrafficLogRepository


class WafIngestUseCase:
    """Thin wrapper that converts WAF events into the existing triage flow."""

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
        stale_processing_timeout_seconds: int = 30,
        enable_preprocessing: bool = True,
    ):
        self._triage = TriageUseCase(
            classifier=classifier,
            repository=repository,
            stale_processing_timeout_seconds=stale_processing_timeout_seconds,
            enable_preprocessing=enable_preprocessing,
        )

    async def execute(
        self,
        *,
        transaction_id: str,
        timestamp: datetime,
        ingest_source: str = "modsec_audit_bridge",
        source_ip: str,
        request_method: str,
        request_path: str,
        request_headers: dict[str, str] | None = None,
        sanitized_body: str = "",
        crs_score: int,
        crs_rule_ids: list[str],
        query_string: str | None = None,
        matched_rule_messages: list[str] | None = None,
        matched_rule_tags: list[str] | None = None,
    ) -> TriageResult:
        uri = request_path
        if query_string:
            uri = f"{request_path}?{query_string}"
        http_request = f"{request_method} {uri} HTTP/1.1"

        sanitized_headers: dict[str, str] = {}
        if request_headers or sanitized_body:
            sanitized = sanitize_waf_event(
                {
                    "request_headers": request_headers or {},
                    "sanitized_body": sanitized_body,
                }
            )
            sanitized_headers = sanitized.get("request_headers") or {}
            sanitized_body = sanitized.get("sanitized_body") or ""

        command = TriageIngestCommand(
            transaction_id=transaction_id,
            timestamp=timestamp,
            source_ip=source_ip,
            request_method=request_method,
            request_uri=request_path,
            request_headers=sanitized_headers,
            request_body=sanitized_body,
            http_request=http_request,
            crs_score=crs_score,
            crs_rule_ids=crs_rule_ids,
            ingest_source=ingest_source,
            matched_rule_messages=matched_rule_messages,
            matched_rule_tags=matched_rule_tags,
            query_string=query_string,
        )

        return await self._triage.ingest(command)
