from __future__ import annotations

from dataclasses import dataclass

import pytest

from web_app.notifications.models import ProviderSendResult
from web_app.notifications.smoke import (
    APPROVED_SMOKE_RECIPIENT,
    LiveSmokeConfigurationError,
    LiveSmokeDisabled,
    run_live_smoke,
    run_smoke_cli,
)


@dataclass
class SmokeSettings:
    resend_live_test_enabled: bool = False
    resend_api_key: str | None = None
    resend_from_email: str = "onboarding@resend.dev"
    resend_smoke_test_to: str | None = APPROVED_SMOKE_RECIPIENT


class ProviderStub:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return ProviderSendResult(message_id="safe-provider-id")


@pytest.mark.asyncio
async def test_live_smoke_is_disabled_without_explicit_flag() -> None:
    provider = ProviderStub()
    with pytest.raises(LiveSmokeDisabled):
        await run_live_smoke(SmokeSettings(), provider=provider)
    assert provider.messages == []


@pytest.mark.asyncio
async def test_live_smoke_refuses_every_other_recipient() -> None:
    provider = ProviderStub()
    settings = SmokeSettings(
        resend_live_test_enabled=True,
        resend_api_key="configured",
        resend_smoke_test_to="other@example.test",
    )
    with pytest.raises(LiveSmokeConfigurationError):
        await run_live_smoke(settings, provider=provider)
    assert provider.messages == []


@pytest.mark.asyncio
async def test_live_smoke_uses_only_locked_harmless_content() -> None:
    provider = ProviderStub()
    result = await run_live_smoke(
        SmokeSettings(
            resend_live_test_enabled=True,
            resend_api_key="configured",
        ),
        provider=provider,
    )

    assert result.message_id == "safe-provider-id"
    assert len(provider.messages) == 1
    message = provider.messages[0]
    assert message.recipient == APPROVED_SMOKE_RECIPIENT
    assert message.subject == "CyberTrace Resend smoke test"
    assert message.text == "This is a development-only provider connectivity test."
    for prohibited in ("otp", "reset", "setup", "password", "account", "waf"):
        assert prohibited not in message.text.lower()


@pytest.mark.asyncio
async def test_smoke_cli_reports_safe_skip_without_configuration_values(capsys) -> None:
    settings = SmokeSettings(
        resend_live_test_enabled=False,
        resend_api_key="must-not-print",
    )

    exit_code = await run_smoke_cli(settings, provider=ProviderStub())

    assert exit_code == 2
    output = capsys.readouterr().out
    assert output.strip() == "SKIP: live Resend smoke test is disabled"
    assert "must-not-print" not in output
