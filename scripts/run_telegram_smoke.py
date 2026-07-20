"""Run the explicitly guarded Telegram provider connectivity smoke test."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_app.config import get_settings
from web_app.notifications.models import ProviderSendResult, TelegramMessage
from web_app.notifications.telegram import TelegramProvider

_SMOKE_TEXT = "CyberTrace development-only Telegram provider connectivity test."


class TelegramSmokeDisabled(RuntimeError):
    pass


class TelegramSmokeConfigurationError(RuntimeError):
    pass


class SmokeSettings(Protocol):
    telegram_live_test_enabled: bool
    telegram_bot_token: str | None
    telegram_chat_id: str | None


class TelegramSender(Protocol):
    async def send(self, message: TelegramMessage) -> ProviderSendResult: ...
    async def close(self) -> None: ...


async def run_live_smoke(
    settings: SmokeSettings,
    *,
    provider: TelegramSender | None = None,
) -> ProviderSendResult:
    if not settings.telegram_live_test_enabled:
        raise TelegramSmokeDisabled("live Telegram smoke test is disabled")
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramSmokeConfigurationError(
            "live Telegram smoke configuration is incomplete"
        )
    owns_provider = provider is None
    sender = provider or TelegramProvider(bot_token=settings.telegram_bot_token)
    try:
        return await sender.send(
            TelegramMessage(chat_id=settings.telegram_chat_id, text=_SMOKE_TEXT)
        )
    finally:
        if owns_provider:
            await sender.close()


async def run_smoke_cli(
    settings: SmokeSettings,
    *,
    provider: TelegramSender | None = None,
) -> int:
    try:
        result = await run_live_smoke(settings, provider=provider)
    except TelegramSmokeDisabled:
        print("SKIP: live Telegram smoke test is disabled")
        return 2
    except TelegramSmokeConfigurationError:
        print("FAIL: live Telegram smoke configuration is incomplete")
        return 1
    except Exception as exc:
        print(f"FAIL: Telegram provider smoke failed ({type(exc).__name__})")
        return 1
    print(f"PASS: Telegram provider accepted smoke message {result.message_id}")
    return 0


def main() -> int:
    return asyncio.run(run_smoke_cli(get_settings()))


if __name__ == "__main__":
    raise SystemExit(main())
