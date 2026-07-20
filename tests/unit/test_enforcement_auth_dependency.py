from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from web_app.presentation.dependencies import auth


def _credentials(token: str, scheme: str = "Bearer") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)


@pytest.mark.asyncio
@pytest.mark.parametrize("credentials", [None, _credentials("wrong"), _credentials("valid", "Basic")])
async def test_enforcement_check_rejects_missing_wrong_or_non_bearer_credentials(
    monkeypatch, credentials
) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(
            enforcement_check_api_key="valid",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.verify_enforcement_check_token(credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.asyncio
async def test_enforcement_check_accepts_only_its_dedicated_key(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(
            enforcement_check_api_key="dedicated-enforcement-key",
        ),
    )

    assert (
        await auth.verify_enforcement_check_token(
            _credentials("dedicated-enforcement-key")
        )
        is None
    )
