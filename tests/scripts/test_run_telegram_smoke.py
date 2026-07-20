from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util

import pytest

from web_app.notifications.models import ProviderSendResult


def smoke_module():
    assert importlib.util.find_spec("scripts.run_telegram_smoke") is not None
    return importlib.import_module("scripts.run_telegram_smoke")


@dataclass
class Settings:
    telegram_live_test_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


class ProviderStub:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return ProviderSendResult(message_id="123")

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_smoke_refuses_without_explicit_live_flag() -> None:
    smoke = smoke_module()
    provider = ProviderStub()

    with pytest.raises(smoke.TelegramSmokeDisabled):
        await smoke.run_live_smoke(Settings(), provider=provider)

    assert provider.messages == []


@pytest.mark.asyncio
async def test_smoke_requires_complete_configuration() -> None:
    smoke = smoke_module()

    with pytest.raises(smoke.TelegramSmokeConfigurationError):
        await smoke.run_live_smoke(
            Settings(telegram_live_test_enabled=True), provider=ProviderStub()
        )


@pytest.mark.asyncio
async def test_smoke_sends_only_harmless_locked_text() -> None:
    smoke = smoke_module()
    provider = ProviderStub()

    result = await smoke.run_live_smoke(
        Settings(
            telegram_live_test_enabled=True,
            telegram_bot_token="secret-token",
            telegram_chat_id="-100123",
        ),
        provider=provider,
    )

    assert result.message_id == "123"
    assert provider.messages[0].chat_id == "-100123"
    assert provider.messages[0].text == (
        "CyberTrace development-only Telegram provider connectivity test."
    )


@pytest.mark.asyncio
async def test_cli_skip_never_prints_credentials(capsys) -> None:
    smoke = smoke_module()
    settings = Settings(
        telegram_bot_token="secret-token", telegram_chat_id="-100123"
    )

    exit_code = await smoke.run_smoke_cli(settings, provider=ProviderStub())

    assert exit_code == 2
    output = capsys.readouterr().out
    assert output.strip() == "SKIP: live Telegram smoke test is disabled"
    assert "secret-token" not in output
    assert "-100123" not in output
