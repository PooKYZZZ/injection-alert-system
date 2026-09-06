from __future__ import annotations

import logging
from typing import Protocol

from web_app.domain.classification_scope import is_actionable_attack_class
from web_app.notifications.models import PendingNotification
from web_app.notifications.outbox import (
    build_telegram_threat_notification,
    build_threat_notification,
)
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)


class ThreatNotificationSettings(Protocol):
    threat_email_enabled: bool
    threat_email_to: str | None
    threat_telegram_enabled: bool
    telegram_available: bool
    telegram_chat_id: str | None
    notification_timezone: str
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
    if not is_actionable_attack_class(attack_category):
        return False
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


async def enqueue_threat_notifications_safely(
    *,
    repository: NotificationEnqueuer,
    settings: ThreatNotificationSettings,
    alert_id: int,
    timestamp: str,
    attack_category: str,
    confidence_tier: str,
    confidence: float,
    action_taken: str,
    request_method: str,
    request_path: str,
) -> bool:
    if not is_actionable_attack_class(attack_category):
        return False
    email_queued = await enqueue_threat_notification_safely(
        repository=repository,
        settings=settings,
        alert_id=alert_id,
        timestamp=timestamp,
        attack_category=attack_category,
        confidence_tier=confidence_tier,
        action_taken=action_taken,
        request_path=request_path,
    )
    telegram_queued = await _enqueue_telegram_threat_safely(
        repository=repository,
        settings=settings,
        alert_id=alert_id,
        timestamp=timestamp,
        attack_category=attack_category,
        confidence_tier=confidence_tier,
        confidence=confidence,
        request_method=request_method,
        request_path=request_path,
    )
    return email_queued or telegram_queued


async def _enqueue_telegram_threat_safely(
    *,
    repository: NotificationEnqueuer,
    settings: ThreatNotificationSettings,
    alert_id: int,
    timestamp: str,
    attack_category: str,
    confidence_tier: str,
    confidence: float,
    request_method: str,
    request_path: str,
) -> bool:
    if not is_actionable_attack_class(attack_category):
        return False
    if confidence_tier not in {"HIGH", "CRITICAL"}:
        return False
    if not settings.threat_telegram_enabled:
        return False
    if not settings.telegram_available or not settings.telegram_chat_id:
        log_event(
            logger,
            "notification.telegram_unavailable",
            "Telegram notification channel is unavailable",
            level="ERROR",
            alert_id=alert_id,
            channel="telegram",
        )
        return False
    notification = build_telegram_threat_notification(
        alert_id=alert_id,
        timestamp=timestamp,
        attack_category=attack_category,
        confidence_tier=confidence_tier,
        confidence=confidence,
        request_method=request_method,
        request_path=request_path,
        dashboard_base_url=settings.dashboard_base_url,
        recipient=settings.telegram_chat_id,
        display_timezone=settings.notification_timezone,
    )
    try:
        created = await repository.enqueue(notification)
    except Exception as exc:
        log_event(
            logger,
            "notification.telegram_enqueue_failed",
            "Telegram notification enqueue failed",
            level="WARNING",
            alert_id=alert_id,
            channel="telegram",
            error_class=type(exc).__name__,
        )
        return False
    log_event(
        logger,
        (
            "notification.telegram_queued"
            if created
            else "notification.telegram_duplicate_suppressed"
        ),
        (
            "Telegram notification queued"
            if created
            else "Duplicate Telegram notification suppressed"
        ),
        alert_id=alert_id,
        confidence_tier=confidence_tier,
        channel="telegram",
        created=created,
    )
    return created
