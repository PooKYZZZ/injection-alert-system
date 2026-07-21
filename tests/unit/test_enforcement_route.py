from types import SimpleNamespace

import pytest

import web_app.presentation.api.routes as routes
from web_app.presentation.schemas import EnforcementCheckRequest


class EmptyRepository:
    async def find_effective_active(self, **kwargs):
        return None


@pytest.mark.asyncio
async def test_enforcement_check_returns_exact_allow_response(monkeypatch):
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: SimpleNamespace(enforcement_mode="shadow"),
    )

    response = await routes.check_shadow_enforcement(
        EnforcementCheckRequest(scope="RECORD_SEARCH", source_ip="203.0.113.10"),
        repository=EmptyRepository(),
    )

    assert response.model_dump(exclude_none=True) == {"decision": "ALLOW"}


def test_enforcement_check_request_rejects_extra_fields():
    with pytest.raises(ValueError):
        EnforcementCheckRequest(
            scope="RECORD_SEARCH",
            source_ip="203.0.113.10",
            action="BLOCK",
        )
