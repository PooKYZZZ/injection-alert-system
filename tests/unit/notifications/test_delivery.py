from __future__ import annotations

from dataclasses import replace
import importlib
import importlib.util

import pytest

from web_app.notifications.models import OutboxJob, ProviderSendResult
from tests.unit.notifications.test_worker import job


def delivery_module():
    assert importlib.util.find_spec("web_app.notifications.delivery") is not None
    return importlib.import_module("web_app.notifications.delivery")


class CapturingProvider:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return ProviderSendResult(message_id="provider-1")

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_router_delivers_email_through_existing_renderer() -> None:
    delivery = delivery_module()
    assert hasattr(delivery, "DeliveryRouter")
    email = CapturingProvider()
    router = delivery.DeliveryRouter(email_provider=email)

    result = await router.deliver(job(), job().safe_payload)

    assert result.message_id == "provider-1"
    assert email.messages[0].recipient == "soc@example.test"


@pytest.mark.asyncio
async def test_router_delivers_telegram_through_telegram_renderer() -> None:
    delivery = delivery_module()
    assert hasattr(delivery, "DeliveryRouter")
    telegram = CapturingProvider()
    router = delivery.DeliveryRouter(email_provider=CapturingProvider(), telegram_provider=telegram)
    telegram_job: OutboxJob = replace(
        job(),
        channel="telegram",
        recipient="-100123",
        safe_payload={
            "event_id": "42",
            "timestamp": "2026-07-20T09:00:00Z",
            "attack_category": "SQL Injection",
            "confidence_tier": "HIGH",
            "confidence": 0.874,
            "request_method": "GET",
            "route_path": "/records/search",
            "dashboard_url": "https://app.example.test/alerts/42",
        },
    )

    result = await router.deliver(telegram_job, telegram_job.safe_payload)

    assert result.message_id == "provider-1"
    assert telegram.messages[0].chat_id == "-100123"


@pytest.mark.asyncio
async def test_router_fails_closed_when_telegram_is_unavailable() -> None:
    delivery = delivery_module()
    router = delivery.DeliveryRouter(email_provider=CapturingProvider())
    telegram_job = replace(job(), channel="telegram", recipient="-100123")

    with pytest.raises(delivery.NotificationProviderError) as captured:
        await router.deliver(telegram_job, telegram_job.safe_payload)

    assert captured.value.error_class == "telegram_unavailable"
    assert captured.value.retryable is False
