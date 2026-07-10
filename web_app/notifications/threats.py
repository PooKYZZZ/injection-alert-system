from __future__ import annotations

import logging
from typing import Protocol

from web_app.notifications.models import PendingNotification
from web_app.notifications.outbox import build_threat_notification

logger = logging.getLogger(__name__)


class ThreatNotificationSettings(Protocol):
    threat_email_enabled: bool
    threat_email_to: str | None
    dashboard_base_url: str


class NotificationEnqueuer(Protocol):
    async def enqueue(self, notification: PendingNotification) -> bool: ...


async def enqueue_threat_notification_safely(
    *,
    repository: NotificationEnqueuer,
    settings: ThreatNotificationSettings,
    alert_id: int,
    timestamp: str,
    attack_category: str,
    confidence_tier: str,
    action_taken: str,
    request_path: str,
) -> bool:
    if not settings.threat_email_enabled or not settings.threat_email_to:
        return False
    notification = build_threat_notification(
        alert_id=alert_id,
        timestamp=timestamp,
        attack_category=attack_category,
        confidence_tier=confidence_tier,
        action_taken=action_taken,
        request_path=request_path,
        dashboard_base_url=settings.dashboard_base_url,
        recipient=settings.threat_email_to,
    )
    try:
        return await repository.enqueue(notification)
    except Exception as exc:
        logger.warning(
            "threat notification enqueue failed",
            extra={"error_type": type(exc).__name__, "alert_id": alert_id},
        )
        return False
