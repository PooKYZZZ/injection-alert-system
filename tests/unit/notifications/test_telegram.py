from __future__ import annotations

import importlib
import importlib.util
import json

import httpx
import pytest

from web_app.notifications.models import TelegramMessage


def telegram_module():
    assert importlib.util.find_spec("web_app.notifications.telegram") is not None
    return importlib.import_module("web_app.notifications.telegram")


def payload() -> dict[str, object]:
    return {
        "event_id": "1849",
        "timestamp": "2026-07-20T08:45:31Z",
        "attack_category": "SQL Injection",
        "confidence_tier": "CRITICAL",
        "confidence": 0.961,
        "request_method": "POST",
        "route_path": "/records/search",
        "dashboard_url": "https://app.example.test/alerts/1849",
        "display_timezone": "Asia/Manila",
    }


def test_renderer_uses_plain_text_and_confidence_tier_wording() -> None:
    telegram = telegram_module()
    assert hasattr(telegram, "render_telegram_threat")

    message = telegram.render_telegram_threat("-100123", payload(), 2)

    assert "CRITICAL SECURITY ALERT" in message.text
    assert "Confidence: 96.1% (CRITICAL)" in message.text
    assert "Request: POST /records/search" in message.text
    assert "Time: Jul 20, 2026, 4:45 PM Asia/Manila" in message.text
    assert "Review alert:" in message.text
    assert "source" not in message.text.lower()


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-12T05:34:22+00:00",
        "2026-08-12T13:34:22+08:00",
    ],
)
def test_renderer_preserves_the_instant_when_localizing_timestamp(
    timestamp: str,
) -> None:
    telegram = telegram_module()
    alert_payload = payload() | {"timestamp": timestamp}

    message = telegram.render_telegram_threat("-100123", alert_payload, 2)

    assert "Time: Aug 12, 2026, 1:34 PM Asia/Manila" in message.text


@pytest.mark.parametrize("timestamp", ["not-a-timestamp", "2026-08-12T05:34:22"])
def test_renderer_rejects_malformed_or_timezone_naive_timestamp(timestamp: str) -> None:
    telegram = telegram_module()

    with pytest.raises(telegram.TelegramPayloadError):
        telegram.render_telegram_threat(
            "-100123", payload() | {"timestamp": timestamp}, 2
        )


def test_renderer_keeps_pending_version_one_messages_deliverable() -> None:
    telegram = telegram_module()
    legacy_payload = payload()
    del legacy_payload["display_timezone"]

    message = telegram.render_telegram_threat("-100123", legacy_payload, 1)

    assert "Time: 2026-07-20T08:45:31Z" in message.text


@pytest.mark.asyncio
async def test_provider_sends_json_without_parse_mode() -> None:
    telegram = telegram_module()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = telegram.TelegramProvider(bot_token="token", client=client)
        result = await provider.send(TelegramMessage("-100123", "Safe text"))

    assert result.message_id == "123"
    assert captured["payload"] == {
        "chat_id": "-100123",
        "text": "Safe text",
        "link_preview_options": {"is_disabled": True},
    }
    assert "parse_mode" not in captured["payload"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_class", "retryable"),
    [
        (400, "telegram_request_invalid", False),
        (401, "telegram_auth_failed", False),
        (403, "telegram_destination_invalid", False),
        (500, "telegram_server_error", True),
    ],
)
async def test_provider_classifies_http_failures(
    status: int, error_class: str, retryable: bool
) -> None:
    telegram = telegram_module()
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"ok": False, "description": "unsafe"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = telegram.TelegramProvider(bot_token="token", client=client)
        with pytest.raises(telegram.NotificationProviderError) as captured:
            await provider.send(TelegramMessage("-100123", "Safe text"))

    assert captured.value.error_class == error_class
    assert captured.value.retryable is retryable
    assert "unsafe" not in str(captured.value)


@pytest.mark.asyncio
async def test_provider_honors_bounded_retry_after() -> None:
    telegram = telegram_module()
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"ok": False, "parameters": {"retry_after": 99999}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = telegram.TelegramProvider(bot_token="token", client=client)
        with pytest.raises(telegram.NotificationProviderError) as captured:
            await provider.send(TelegramMessage("-100123", "Safe text"))

    assert captured.value.error_class == "telegram_rate_limited"
    assert captured.value.retryable is True
    assert captured.value.retry_after_seconds == 3600


@pytest.mark.asyncio
async def test_read_timeout_is_ambiguous_and_not_retryable() -> None:
    telegram = telegram_module()
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret detail", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = telegram.TelegramProvider(bot_token="token", client=client)
        with pytest.raises(telegram.NotificationProviderError) as captured:
            await provider.send(TelegramMessage("-100123", "Safe text"))

    assert captured.value.error_class == "telegram_delivery_ambiguous"
    assert captured.value.retryable is False
    assert captured.value.delivery_ambiguous is True


@pytest.mark.asyncio
async def test_malformed_success_is_ambiguous() -> None:
    telegram = telegram_module()
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = telegram.TelegramProvider(bot_token="token", client=client)
        with pytest.raises(telegram.NotificationProviderError) as captured:
            await provider.send(TelegramMessage("-100123", "Safe text"))

    assert captured.value.delivery_ambiguous is True
    assert captured.value.retryable is False
