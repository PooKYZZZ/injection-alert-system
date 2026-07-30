import logging
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from web_app.domain.source_address import (
    SourceProvenance,
    canonicalize_source_ip,
)
from web_app.observability.structured_logging import log_event

IngestSource = Literal["modsec_audit_bridge"]
logger = logging.getLogger(__name__)


class WafIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingest_source: IngestSource = Field(
        ..., description="Source of the WAF event ingestion"
    )
    transaction_id: str = Field(
        ..., min_length=1, max_length=128, description="Unique transaction ID for dedup"
    )
    timestamp: datetime | None = Field(
        default=None, description="ISO 8601 source timestamp of the event"
    )
    source_ip: str | None = Field(default=None, description="Canonical source IP")
    source_provenance: SourceProvenance
    cf_connecting_ip_matches_client_ip: bool | None = None
    request_method: str = Field(
        ..., min_length=1, max_length=16, description="HTTP request method"
    )
    request_path: str = Field(
        ..., min_length=1, max_length=512, description="HTTP request path"
    )
    crs_score: int = Field(..., ge=0, description="ModSecurity CRS anomaly score")
    crs_rule_ids: list[str] = Field(
        ..., min_length=1, description="List of triggered CRS rule IDs"
    )
    query_string: str | None = Field(
        default=None, max_length=4096, description="HTTP query string"
    )
    request_headers: dict[str, str] | None = Field(
        default=None, description="HTTP request headers"
    )
    sanitized_body: str | None = Field(
        default=None, max_length=1024, description="Sanitized request body"
    )
    matched_rule_messages: list[str] | None = Field(
        default=None, description="Messages from matched WAF rules"
    )
    matched_rule_tags: list[str] | None = Field(
        default=None, description="Tags from matched WAF rules"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_source_timestamp(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamp must include an explicit UTC offset")
            return value.astimezone(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            log_event(
                logger,
                "waf_ingest.source_timestamp_invalid",
                "WAF source timestamp is invalid; canonical value is null",
                level="WARNING",
                component="waf-ingest-schema",
            )
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp must include an explicit UTC offset")
        return parsed.astimezone(timezone.utc)

    @field_validator("source_ip", mode="before")
    @classmethod
    def canonicalize_source(cls, value):
        return canonicalize_source_ip(value)

    @model_validator(mode="after")
    def validate_source_evidence(self) -> "WafIngestRequest":
        if self.source_provenance is SourceProvenance.LEGACY_UNKNOWN:
            raise ValueError("LEGACY_UNKNOWN is not valid for live WAF ingest")
        if (
            self.source_provenance is SourceProvenance.DIRECT_REMOTE_ADDR
            and self.cf_connecting_ip_matches_client_ip is not None
        ):
            raise ValueError(
                "direct source provenance requires a null Cloudflare match value"
            )
        return self
