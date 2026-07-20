import pytest
from pydantic import ValidationError

from web_app.presentation.schemas import EnforcementCheckRequest


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
