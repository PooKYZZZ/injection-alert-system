from __future__ import annotations

from dataclasses import dataclass

import pytest

from web_app.notifications import threats
from web_app.notifications.threats import enqueue_threat_notification_safely


@dataclass
class ThreatSettings:
    threat_email_enabled: bool = True
    threat_email_to: str | None = "soc@example.test"
    threat_telegram_enabled: bool = True
    telegram_available: bool = True
    telegram_chat_id: str | None = "-100123"
    dashboard_base_url: str = "https://dashboard.example.test"


class FailingRepository:
    async def enqueue(self, _notification):
        raise RuntimeError("database URL and secret detail")


class CapturingRepository:
    def __init__(self) -> None:
        self.notification = None
        self.notifications = []

    async def enqueue(self, notification):
        self.notification = notification
        self.notifications.append(notification)
        return True


@pytest.mark.asyncio
async def test_threat_enqueue_failure_does_not_escape_request_boundary() -> None:
    queued = await enqueue_threat_notification_safely(
        repository=FailingRepository(),
        settings=ThreatSettings(),
        alert_id=42,
        timestamp="2026-07-10T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier="HIGH",
        action_taken="BLOCKED",
        request_path="/records/search?unsafe=1",
    )

    assert queued is False


@pytest.mark.asyncio
async def test_threat_enqueue_uses_safe_payload() -> None:
    repository = CapturingRepository()
    queued = await enqueue_threat_notification_safely(
        repository=repository,
        settings=ThreatSettings(),
        alert_id=42,
        timestamp="2026-07-10T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier="HIGH",
        action_taken="BLOCKED",
        request_path="/records/search?unsafe=1",
    )

    assert queued is True
    assert repository.notification.safe_payload["route_path"] == "/records/search"


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence_tier", ["HIGH", "CRITICAL"])
async def test_high_confidence_tiers_enqueue_email_and_telegram(
    confidence_tier: str,
) -> None:
    assert hasattr(threats, "enqueue_threat_notifications_safely")
    repository = CapturingRepository()

    queued = await threats.enqueue_threat_notifications_safely(
        repository=repository,
        settings=ThreatSettings(),
        alert_id=42,
        timestamp="2026-07-20T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier=confidence_tier,
        confidence=0.95,
        action_taken="BLOCKED",
        request_method="POST",
        request_path="/records/search?unsafe=1",
    )

    assert queued is True
    assert [item.channel for item in repository.notifications] == [
        "email",
        "telegram",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence_tier", ["LOW", "MEDIUM"])
async def test_lower_confidence_tiers_never_enqueue_telegram(
    confidence_tier: str,
) -> None:
    repository = CapturingRepository()

    await threats.enqueue_threat_notifications_safely(
        repository=repository,
        settings=ThreatSettings(),
        alert_id=42,
        timestamp="2026-07-20T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier=confidence_tier,
        confidence=0.60,
        action_taken="ALLOWED",
        request_method="GET",
        request_path="/records/search",
    )

    assert [item.channel for item in repository.notifications] == ["email"]


class EmailFailingRepository(CapturingRepository):
    async def enqueue(self, notification):
        self.notifications.append(notification)
        if notification.channel == "email":
            raise RuntimeError("email enqueue unavailable")
        return True


@pytest.mark.asyncio
async def test_email_enqueue_failure_does_not_prevent_telegram_attempt() -> None:
    repository = EmailFailingRepository()

    queued = await threats.enqueue_threat_notifications_safely(
        repository=repository,
        settings=ThreatSettings(),
        alert_id=42,
        timestamp="2026-07-20T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier="HIGH",
        confidence=0.91,
        action_taken="BLOCKED",
        request_method="POST",
        request_path="/records/search",
    )

    assert queued is True
    assert [item.channel for item in repository.notifications] == [
        "email",
        "telegram",
    ]
