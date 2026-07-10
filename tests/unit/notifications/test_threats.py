from __future__ import annotations

from dataclasses import dataclass

import pytest

from web_app.notifications.threats import enqueue_threat_notification_safely


@dataclass
class ThreatSettings:
    threat_email_enabled: bool = True
    threat_email_to: str | None = "soc@example.test"
    dashboard_base_url: str = "https://dashboard.example.test"


class FailingRepository:
    async def enqueue(self, _notification):
        raise RuntimeError("database URL and secret detail")


class CapturingRepository:
    def __init__(self) -> None:
        self.notification = None

    async def enqueue(self, notification):
        self.notification = notification
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
