from typing import Literal

from pydantic import BaseModel, ConfigDict, IPvAnyAddress


class EnforcementCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["RECORD_SEARCH"]
    source_ip: IPvAnyAddress


class EnforcementCheckResponse(BaseModel):
    decision: Literal["ALLOW"]
