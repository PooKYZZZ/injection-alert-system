from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from web_app.presentation.dependencies import auth


def _credentials(token: str, scheme: str = "Bearer") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)


@pytest.mark.asyncio
async def test_missing_waf_key_is_unauthorized(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(waf_ingest_api_key=""),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.verify_waf_ingest_token(_credentials("any-token"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.asyncio
async def test_general_internal_key_is_rejected_for_waf_ingest(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(waf_ingest_api_key="dedicated-waf-key"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.verify_waf_ingest_token(_credentials("general-internal-key"))

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_correct_waf_key_is_accepted(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(waf_ingest_api_key="dedicated-waf-key"),
    )

    assert await auth.verify_waf_ingest_token(_credentials("dedicated-waf-key")) is None


@pytest.mark.asyncio
async def test_non_bearer_waf_credentials_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(waf_ingest_api_key="dedicated-waf-key"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.verify_waf_ingest_token(
            _credentials("dedicated-waf-key", scheme="Basic")
        )

    assert exc_info.value.status_code == 401
