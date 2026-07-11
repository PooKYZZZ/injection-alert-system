from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.notifications.models import OutboxJob, PendingNotification


class LeaseLostError(RuntimeError):
    pass


class PostgresNotificationOutboxRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim_batch(
        self, worker_id: str, batch_size: int, lease_seconds: int
    ) -> list[OutboxJob]:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
SELECT * FROM public.claim_notification_outbox_batch_v61(
  :worker_id, :batch_size, :lease_seconds
)
"""
                    ),
                    {
                        "worker_id": worker_id,
                        "batch_size": batch_size,
                        "lease_seconds": lease_seconds,
                    },
                )
                rows = result.mappings().all()
        return [
            OutboxJob(
                id=str(row["id"]),
                kind=row["kind"],
                recipient=row["recipient"],
                safe_payload=row["payload_safe_json"],
                template_version=row["template_version"],
                dedupe_key=row["dedupe_key"],
                provider_idempotency_key=row["provider_idempotency_key"],
                attempt_count=row["attempts"],
                max_attempts=row["max_attempts"],
                deliver_before=row.get("deliver_before"),
            )
            for row in rows
        ]

    async def complete(
        self, job_id: str, worker_id: str, message_id: str
    ) -> None:
        changed = await self._transition(
            """
SELECT public.complete_notification_outbox_job_v61(
  :job_id, :worker_id, :message_id
)
""",
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "message_id": message_id,
            },
        )
        if not changed:
            raise LeaseLostError("Notification outbox lease is no longer active.")

    async def fail(
        self,
        job_id: str,
        worker_id: str,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
    ) -> None:
        changed = await self._transition(
            """
SELECT public.fail_notification_outbox_job_v61(
  :job_id, :worker_id, :error_class, :retryable, :retry_delay_seconds
)
""",
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "error_class": error_class,
                "retryable": retryable,
                "retry_delay_seconds": retry_delay_seconds,
            },
        )
        if not changed:
            raise LeaseLostError("Notification outbox lease is no longer active.")

    async def enqueue(self, notification: PendingNotification) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
INSERT INTO public.notification_outbox (
  kind, channel, recipient, status, payload_safe_json,
  template_version, dedupe_key, provider_idempotency_key, deliver_before
)
VALUES (
  :kind, 'email', :recipient, 'pending',
  CAST(:safe_payload AS jsonb), :template_version,
  :dedupe_key, :provider_idempotency_key,
  COALESCE(:deliver_before, now() + interval '24 hours')
)
ON CONFLICT (dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING
RETURNING id
"""
                    ),
                    {
                        "kind": notification.kind,
                        "recipient": notification.recipient,
                        "safe_payload": json.dumps(
                            notification.safe_payload,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                        "template_version": notification.template_version,
                        "dedupe_key": notification.dedupe_key,
                        "provider_idempotency_key": notification.provider_idempotency_key,
                        "deliver_before": notification.deliver_before,
                    },
                )
                return result.scalar_one_or_none() is not None

    async def _transition(self, sql: str, params: dict[str, Any]) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(text(sql), params)
                return bool(result.scalar_one())


def build_threat_notification(
    *,
    alert_id: int,
    timestamp: str,
    attack_category: str,
    confidence_tier: str,
    action_taken: str,
    request_path: str,
    dashboard_base_url: str,
    recipient: str,
) -> PendingNotification:
    safe_path = request_path.split("?", 1)[0].split("#", 1)[0]
    if not safe_path.startswith("/"):
        safe_path = "/"
    key = f"threat/{alert_id}"
    return PendingNotification(
        kind="threat_detected",
        recipient=recipient,
        safe_payload={
            "event_id": str(alert_id),
            "timestamp": timestamp,
            "attack_category": attack_category,
            "confidence_tier": confidence_tier,
            "action_taken": action_taken,
            "route_path": safe_path,
            "dashboard_url": f"{dashboard_base_url.rstrip('/')}/alerts/{alert_id}",
        },
        template_version=1,
        dedupe_key=key,
        provider_idempotency_key=key,
    )
