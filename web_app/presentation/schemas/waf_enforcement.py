from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from web_app.domain.waf_state import canonicalize_waf_source_ip


class WafSnapshotItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: int = Field(ge=1)
    recommendation_id: int = Field(ge=1)
    source_ip: str = Field(min_length=1, max_length=45)
    request_path: str = Field(min_length=1, max_length=512)
    expires_at: datetime

    @field_validator("source_ip")
    @classmethod
    def validate_source_ip(cls, value: str) -> str:
        canonical = canonicalize_waf_source_ip(value)
        if canonical is None:
            raise ValueError("valid source IP required")
        return canonical

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTC-aware datetime required")
        return value


class WafSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    policy_version: Literal["confidence-waf-enforcement-v1"]
    revision: int = Field(ge=0)
    scope: Literal["RECORD_SEARCH"]
    generated_at: datetime
    state_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    items: list[WafSnapshotItem] = Field(max_length=512)

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTC-aware datetime required")
        return value
