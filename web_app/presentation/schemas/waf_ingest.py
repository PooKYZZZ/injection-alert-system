from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IngestSource = Literal["modsec_audit_bridge"]


class WafIngestRequest(BaseModel):
    ingest_source: IngestSource = Field(
        ..., description="Source of the WAF event ingestion"
    )
    transaction_id: str = Field(
        ..., min_length=1, max_length=128, description="Unique transaction ID for dedup"
    )
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the event")
    source_ip: str = Field(
        ..., min_length=1, max_length=45, description="Source IP address"
    )
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
