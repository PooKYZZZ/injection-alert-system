from __future__ import annotations

import json

import httpx
import pytest

from web_app.notifications.models import EmailMessage
from web_app.notifications.providers import (
    EmailProviderError,
    FakeEmailProvider,
    ResendEmailProvider,
)


@pytest.mark.asyncio
async def test_fake_provider_captures_message_without_network() -> None:
    provider = FakeEmailProvider()
    message = EmailMessage(
        recipient="analyst@example.test",
        subject="Security notice",
        text="Safe text",
        html="<p>Safe text</p>",
        idempotency_key="security-event/event-1",
    )

    result = await provider.send(message)

    assert provider.messages == [message]
    assert result.message_id == "fake-1"


@pytest.mark.asyncio
async def test_resend_provider_maps_safe_contract_and_idempotency_key() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["idempotency"] = request.headers["Idempotency-Key"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "provider-message-1"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.resend.com",
    ) as client:
        provider = ResendEmailProvider(
            api_key="test-api-key",
            from_email="CyberTrace <security@example.test>",
            client=client,
        )
        result = await provider.send(
            EmailMessage(
                recipient="viewer@example.test",
                subject="CyberTrace notice",
                text="Safe text",
                html="<p>Safe text</p>",
                idempotency_key="notice/event-2",
            )
        )

    assert result.message_id == "provider-message-1"
    assert captured == {
        "authorization": "Bearer test-api-key",
        "idempotency": "notice/event-2",
        "payload": {
            "from": "CyberTrace <security@example.test>",
            "to": ["viewer@example.test"],
            "subject": "CyberTrace notice",
            "text": "Safe text",
            "html": "<p>Safe text</p>",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type", "retryable"),
    [
        (409, "concurrent_idempotent_requests", True),
        (429, "rate_limit_exceeded", True),
        (503, "application_error", True),
        (400, "validation_error", False),
        (422, "invalid_from_address", False),
    ],
)
async def test_resend_provider_classifies_failures_without_provider_text(
    status: int, error_type: str, retryable: bool
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"name": error_type, "message": "unsafe provider detail"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.resend.com",
    ) as client:
        provider = ResendEmailProvider(
            api_key="test-api-key",
            from_email="security@example.test",
            client=client,
        )
        with pytest.raises(EmailProviderError) as captured:
            await provider.send(
                EmailMessage(
                    recipient="viewer@example.test",
                    subject="Notice",
                    text="Safe",
                    html="<p>Safe</p>",
                    idempotency_key="notice/event-3",
                )
            )

    assert captured.value.retryable is retryable
    assert captured.value.error_class == error_type
    assert "unsafe provider detail" not in str(captured.value)


@pytest.mark.asyncio
async def test_resend_provider_treats_timeout_as_retryable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret-bearing timeout", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.resend.com",
    ) as client:
        provider = ResendEmailProvider(
            api_key="test-api-key",
            from_email="security@example.test",
            client=client,
        )
        with pytest.raises(EmailProviderError) as captured:
            await provider.send(
                EmailMessage(
                    recipient="viewer@example.test",
                    subject="Notice",
                    text="Safe",
                    html="<p>Safe</p>",
                    idempotency_key="notice/event-4",
                )
            )

    assert captured.value.retryable is True
    assert captured.value.error_class == "provider_timeout"
    assert "secret-bearing" not in str(captured.value)


@pytest.mark.asyncio
async def test_resend_provider_rejects_log_unsafe_message_id() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "provider-id\nforged-log"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.resend.com",
    ) as client:
        provider = ResendEmailProvider(
            api_key="test-api-key",
            from_email="security@example.test",
            client=client,
        )
        with pytest.raises(EmailProviderError) as captured:
            await provider.send(
                EmailMessage(
                    recipient="viewer@example.test",
                    subject="Notice",
                    text="Safe",
                    html="<p>Safe</p>",
                    idempotency_key="notice/event-5",
                )
            )

    assert captured.value.error_class == "provider_malformed_response"
