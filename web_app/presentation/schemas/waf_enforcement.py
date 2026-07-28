from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from web_app.domain.waf_state import canonicalize_waf_source_ip

UTC_MILLIS_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"


class WafSnapshotItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: int = Field(ge=1)
    recommendation_id: int = Field(ge=1)
    source_ip: str = Field(min_length=1, max_length=45)
    request_path: Literal["/records/search"]
    expires_at: str = Field(pattern=UTC_MILLIS_PATTERN)

    @field_validator("source_ip")
    @classmethod
    def validate_source_ip(cls, value: str) -> str:
        canonical = canonicalize_waf_source_ip(value)
        if canonical is None:
            raise ValueError("valid source IP required")
        if canonical != value:
            raise ValueError("canonical source IP required")
        return value


class WafSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    policy_version: Literal["confidence-waf-enforcement-v1"]
    revision: int = Field(ge=0)
    scope: Literal["RECORD_SEARCH"]
    generated_at: str = Field(pattern=UTC_MILLIS_PATTERN)
    state_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    items: list[WafSnapshotItem] = Field(max_length=512)
