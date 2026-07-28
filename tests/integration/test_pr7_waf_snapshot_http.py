from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from web_app.domain.waf_state import canonical_state_checksum
from web_app.infrastructure.database import get_db
from web_app.presentation.api import waf_enforcement_router as module
from web_app.presentation.schemas.waf_enforcement import WafSnapshotResponse


def _client(monkeypatch: pytest.MonkeyPatch, *, enabled: bool = True):
    token = "t" * 32
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            waf_state_sync_enabled=enabled,
            app_env="testing",
            waf_state_sync_api_key=token,
        ),
    )

    async def fake_db():
        yield object()

    app = FastAPI()
    app.include_router(module.router, prefix="/api")
    app.dependency_overrides[get_db] = fake_db
    return TestClient(app), token


def _payload() -> dict[str, object]:
    items = [
        {
            "entry_id": 1,
            "recommendation_id": 2,
            "source_ip": "203.0.113.7",
            "request_path": "/records/search",
            "expires_at": "2026-07-28T00:01:00.123Z",
        }
    ]
    return {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 2,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-28T00:00:00.123Z",
        "state_checksum_sha256": canonical_state_checksum(
            1,
            "confidence-waf-enforcement-v1",
            2,
            "RECORD_SEARCH",
            items,
        ),
        "items": items,
    }


def test_disabled_snapshot_is_real_http_404_with_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client(monkeypatch, enabled=False)
    response = client.get("/api/internal/waf-enforcement/snapshot")
    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"


def test_invalid_token_is_real_http_401_with_bearer_and_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client(monkeypatch)
    response = client.get(
        "/api/internal/waf-enforcement/snapshot",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["cache-control"] == "no-store"


def test_valid_snapshot_uses_wire_timestamps_and_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, token = _client(monkeypatch)

    async def valid_read(_db):
        return _payload()

    monkeypatch.setattr(module, "read_waf_snapshot", valid_read)
    response = client.get(
        "/api/internal/waf-enforcement/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["generated_at"] == "2026-07-28T00:00:00.123Z"
    assert body["items"][0]["expires_at"] == "2026-07-28T00:01:00.123Z"
    checksum_input = {
        key: body[key]
        for key in ("schema_version", "policy_version", "revision", "scope", "items")
    }
    assert body["state_checksum_sha256"] == canonical_state_checksum(
        checksum_input["schema_version"],
        checksum_input["policy_version"],
        checksum_input["revision"],
        checksum_input["scope"],
        checksum_input["items"],
    )


def test_missing_singleton_or_repository_failure_is_real_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, token = _client(monkeypatch)

    async def failed_read(_db):
        raise RuntimeError("WAF enforcement state singleton is missing")

    monkeypatch.setattr(module, "read_waf_snapshot", failed_read)
    response = client.get(
        "/api/internal/waf-enforcement/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert "singleton" not in response.text


def test_invalid_snapshot_payload_is_real_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, token = _client(monkeypatch)
    payload = _payload()
    payload["generated_at"] = "2026-07-28T00:00:00Z"

    async def invalid_read(_db):
        return payload

    monkeypatch.setattr(module, "read_waf_snapshot", invalid_read)
    response = client.get(
        "/api/internal/waf-enforcement/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


def test_oversized_snapshot_is_real_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, token = _client(monkeypatch)
    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 1)

    async def oversized_read(_db):
        return _payload()

    monkeypatch.setattr(module, "read_waf_snapshot", oversized_read)
    response = client.get(
        "/api/internal/waf-enforcement/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert "state_checksum_sha256" not in json.dumps(response.json())


def test_512_bounded_items_fit_and_513_is_rejected() -> None:
    items = [
        {
            "entry_id": index + 1,
            "recommendation_id": index + 1,
            "source_ip": f"10.{index // 256}.{index % 256}.1",
            "request_path": "/records/search",
            "expires_at": "2026-07-28T00:01:00.123Z",
        }
        for index in range(512)
    ]
    payload = {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 2,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-28T00:00:00.123Z",
        "state_checksum_sha256": "0" * 64,
        "items": items,
    }
    model = WafSnapshotResponse.model_validate(payload)
    assert len(model.model_dump_json().encode("utf-8")) < module.MAX_SNAPSHOT_BYTES
    with pytest.raises(ValidationError):
        WafSnapshotResponse.model_validate({**payload, "items": [*items, items[0]]})
