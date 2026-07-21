from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, model_validator


class EnforcementCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["RECORD_SEARCH"]
    source_ip: IPvAnyAddress


class EnforcementCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["ALLOW", "CHALLENGE", "THROTTLE"]
    enforcement_tier: Literal["LOW", "MEDIUM"] | None = None
    retry_after_seconds: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_decision_metadata(self) -> "EnforcementCheckResponse":
        if self.decision == "CHALLENGE":
            if self.enforcement_tier is None or self.retry_after_seconds is not None:
                raise ValueError("CHALLENGE requires only enforcement_tier")
        elif self.decision == "THROTTLE":
            if self.retry_after_seconds is None or self.enforcement_tier is not None:
                raise ValueError("THROTTLE requires only retry_after_seconds")
        elif self.enforcement_tier is not None or self.retry_after_seconds is not None:
            raise ValueError("ALLOW cannot include active enforcement metadata")
        return self


class EnforcementChallengeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["RECORD_SEARCH"]
    source_ip: IPvAnyAddress
    token: str = Field(min_length=1, max_length=2048)


class EnforcementChallengeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool
    status: Literal[
        "VERIFIED",
        "INVALID",
        "UNAVAILABLE",
        "NO_ACTIVE_ENFORCEMENT",
        "SOURCE_INELIGIBLE",
    ]
