import pytest
from pydantic import ValidationError

from web_app.presentation.schemas import (
    EnforcementChallengeRequest,
    EnforcementCheckRequest,
    EnforcementCheckResponse,
)


def test_enforcement_request_normalizes_ip_and_forbids_unknown_fields():
    request = EnforcementCheckRequest(
        scope="RECORD_SEARCH", source_ip="::ffff:192.0.2.10"
    )
    assert str(request.source_ip) == "::ffff:192.0.2.10"
    with pytest.raises(ValidationError):
        EnforcementCheckRequest(
            scope="RECORD_SEARCH", source_ip="192.0.2.10", action="BLOCK"
        )


def test_enforcement_request_rejects_unsupported_scope_or_ip():
    with pytest.raises(ValidationError):
        EnforcementCheckRequest(scope="OTHER", source_ip="192.0.2.10")
    with pytest.raises(ValidationError):
        EnforcementCheckRequest(scope="RECORD_SEARCH", source_ip="invalid")


def test_enforcement_response_models_active_decisions_with_required_metadata():
    assert EnforcementCheckResponse(decision="ALLOW").model_dump(exclude_none=True) == {
        "decision": "ALLOW"
    }
    assert EnforcementCheckResponse(
        decision="CHALLENGE", enforcement_tier="LOW"
    ).model_dump(exclude_none=True) == {
        "decision": "CHALLENGE",
        "enforcement_tier": "LOW",
    }
    assert EnforcementCheckResponse(
        decision="THROTTLE", retry_after_seconds=4
    ).model_dump(exclude_none=True) == {
        "decision": "THROTTLE",
        "retry_after_seconds": 4,
    }
    assert EnforcementCheckResponse(decision="BLOCK").model_dump(
        exclude_none=True
    ) == {"decision": "BLOCK"}
    with pytest.raises(ValidationError):
        EnforcementCheckResponse(decision="CHALLENGE")
    with pytest.raises(ValidationError):
        EnforcementCheckResponse(decision="THROTTLE")
    with pytest.raises(ValidationError):
        EnforcementCheckResponse(decision="BLOCK", enforcement_tier="HIGH")


def test_challenge_request_forbids_tier_and_bounds_token():
    request = EnforcementChallengeRequest(
        scope="RECORD_SEARCH", source_ip="203.0.113.10", token="token"
    )
    assert request.token == "token"
    with pytest.raises(ValidationError):
        EnforcementChallengeRequest(
            scope="RECORD_SEARCH",
            source_ip="203.0.113.10",
            token="token",
            enforcement_tier="LOW",
        )
    with pytest.raises(ValidationError):
        EnforcementChallengeRequest(
            scope="RECORD_SEARCH", source_ip="203.0.113.10", token="x" * 2049
        )
