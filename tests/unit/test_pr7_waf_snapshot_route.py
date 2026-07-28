from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from web_app.presentation.api import waf_enforcement_router as module
from web_app.presentation.schemas.waf_enforcement import WafSnapshotResponse


def _request(authorization: str | None = None) -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request({"type": "http", "headers": headers, "method": "GET", "path": "/"})


def test_waf_state_sync_authentication_uses_bearer_constant_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(waf_state_sync_api_key="x" * 32),
    )
    module.verify_waf_state_sync_authorization(_request("Bearer " + "x" * 32))
    with pytest.raises(HTTPException) as error:
        module.verify_waf_state_sync_authorization(_request("Bearer wrong"))
    assert error.value.status_code == 401


def test_waf_state_sync_authentication_does_not_accept_non_bearer() -> None:
    with pytest.raises(HTTPException) as error:
        module.verify_waf_state_sync_authorization(_request("Basic secret"))
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_disabled_snapshot_returns_404_with_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(waf_state_sync_enabled=False, app_env="development"),
    )
    result = await module.waf_enforcement_snapshot(_request(), Response(), None)
    assert result.status_code == 404
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_snapshot_response_is_typed_and_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "x" * 32
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            waf_state_sync_enabled=True, app_env="testing", waf_state_sync_api_key=token
        ),
    )

    async def fake_read(_db):
        return {
            "schema_version": 1,
            "policy_version": "confidence-waf-enforcement-v1",
            "revision": 2,
            "scope": "RECORD_SEARCH",
            "generated_at": "2026-07-28T00:00:00.000Z",
            "state_checksum_sha256": "0" * 64,
            "items": [],
        }

    monkeypatch.setattr(module, "read_waf_snapshot", fake_read)
    result = await module.waf_enforcement_snapshot(
        _request("Bearer " + token), Response(), None
    )
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_snapshot_response_size_limit_returns_safe_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "x" * 32
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            waf_state_sync_enabled=True,
            app_env="testing",
            waf_state_sync_api_key=token,
        ),
    )

    async def fake_read(_db):
        return {
            "schema_version": 1,
            "policy_version": "confidence-waf-enforcement-v1",
            "revision": 2,
            "scope": "RECORD_SEARCH",
            "generated_at": "2026-07-28T00:00:00.000Z",
            "state_checksum_sha256": "0" * 64,
            "items": [],
        }

    monkeypatch.setattr(module, "read_waf_snapshot", fake_read)
    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 1)
    with pytest.raises(HTTPException) as error:
        await module.waf_enforcement_snapshot(
            _request("Bearer " + token), Response(), None
        )
    assert error.value.status_code == 503


def test_snapshot_wire_schema_keeps_canonical_timestamp_strings() -> None:
    payload = {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 2,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-28T00:00:00.123Z",
        "state_checksum_sha256": "0" * 64,
        "items": [
            {
                "entry_id": 1,
                "recommendation_id": 2,
                "source_ip": "203.0.113.7",
                "request_path": "/records/search",
                "expires_at": "2026-07-28T00:01:00.123Z",
            }
        ],
    }
    model = WafSnapshotResponse.model_validate(payload)
    dumped = model.model_dump(mode="json")
    assert dumped["generated_at"] == payload["generated_at"]
    assert dumped["items"][0]["expires_at"] == payload["items"][0]["expires_at"]


def test_snapshot_wire_schema_rejects_noncanonical_source_ip() -> None:
    payload = {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 2,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-28T00:00:00.000Z",
        "state_checksum_sha256": "0" * 64,
        "items": [
            {
                "entry_id": 1,
                "recommendation_id": 2,
                "source_ip": "::ffff:203.0.113.7",
                "request_path": "/records/search",
                "expires_at": "2026-07-28T00:01:00.123Z",
            }
        ],
    }
    with pytest.raises(ValueError, match="canonical source IP required"):
        WafSnapshotResponse.model_validate(payload)
