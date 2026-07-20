from types import SimpleNamespace

from fastapi.testclient import TestClient

import web_app.presentation.api.routes as routes
import web_app.presentation.dependencies.auth as auth
from web_app.presentation.app import create_app


class EmptyRepository:
    async def find_effective_active(self, **kwargs):
        return None


def test_enforcement_check_requires_its_dedicated_credential(monkeypatch):
    key = "enforcement-key-for-integration-tests-32chars"
    settings = SimpleNamespace(enforcement_check_api_key=key, enforcement_mode="shadow")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    app = create_app()
    app.dependency_overrides[routes.get_enforcement_repository] = lambda: EmptyRepository()
    with TestClient(app) as client:
        missing = client.post(
            "/api/internal/enforcement/check",
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
        valid = client.post(
            "/api/internal/enforcement/check",
            headers={"Authorization": f"Bearer {key}"},
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
    app.dependency_overrides.clear()

    assert missing.status_code == 401
    assert valid.status_code == 200
    assert valid.json() == {"decision": "ALLOW"}
