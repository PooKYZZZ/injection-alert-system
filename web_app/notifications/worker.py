from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Callable, Literal, Protocol

from web_app.notifications.models import OutboxJob, WorkerRunResult
from web_app.notifications.payload_crypto import (
    PROTECTED_NOTIFICATION_KINDS,
    NotificationPayloadError,
    decrypt_notification_payload,
)
from web_app.notifications.delivery import DeliveryRouter
from web_app.notifications.providers import EmailProvider, NotificationProviderError
from web_app.notifications.telegram import TelegramPayloadError
from web_app.notifications.templates import TemplatePayloadError
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)


class OutboxRepository(Protocol):
    async def claim_batch(
        self, worker_id: str, batch_size: int, lease_seconds: int
    ) -> list[OutboxJob]: ...

    async def complete(
        self, job_id: str, worker_id: str, message_id: str
    ) -> None: ...

    async def fail(
        self,
        job_id: str,
        worker_id: str,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
    ) -> None: ...


class OutboxWorker:
    def __init__(
        self,
        *,
        repository: OutboxRepository,
        provider: EmailProvider | None = None,
        delivery: DeliveryRouter | None = None,
        worker_id: str,
        batch_size: int = 1,
        lease_seconds: int = 60,
        base_retry_seconds: int = 30,
        max_retry_seconds: int = 3_600,
        jitter: Callable[[int, int], int] = random.randint,
    ) -> None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("Worker id is invalid.")
        if (provider is None) == (delivery is None):
            raise ValueError("Provide exactly one notification delivery boundary.")
        self._repository = repository
        self._delivery = delivery or DeliveryRouter(email_provider=provider)
        self._worker_id = worker_id
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds
        self._base_retry_seconds = base_retry_seconds
        self._max_retry_seconds = max_retry_seconds
        self._jitter = jitter

    async def run_once(self) -> WorkerRunResult:
        jobs = await self._repository.claim_batch(
            self._worker_id, self._batch_size, self._lease_seconds
        )
        sent = 0
        failed = 0
        ambiguous = 0
        for job in jobs:
            if (
                job.deliver_before is not None
                and job.deliver_before <= datetime.now(timezone.utc)
            ):
                failed += 1
                await self._safe_fail(
                    job,
                    "delivery_deadline_expired",
                    False,
                    0,
                )
                continue
            try:
                payload = job.safe_payload
                if job.kind in PROTECTED_NOTIFICATION_KINDS:
                    payload = decrypt_notification_payload(
                        kind=job.kind,
                        recipient=job.recipient,
                        idempotency_key=job.provider_idempotency_key,
                        envelope=job.safe_payload,
                    )
                result = await self._delivery.deliver(job, payload)
            except NotificationPayloadError:
                failed += 1
                await self._safe_fail(job, "payload_decryption_failed", False, 0)
            except (TemplatePayloadError, TelegramPayloadError):
                failed += 1
                await self._safe_fail(job, "template_payload_invalid", False, 0)
            except NotificationProviderError as exc:
                failed += 1
                retry_delay = (
                    exc.retry_after_seconds
                    if exc.retryable and exc.retry_after_seconds is not None
                    else self._retry_delay(job.attempt_count)
                    if exc.retryable
                    else 0
                )
                await self._safe_fail(
                    job,
                    exc.error_class,
                    exc.retryable,
                    retry_delay,
                )
                self._log_delivery_failure(
                    job=job,
                    error_class=exc.error_class,
                    retryable=exc.retryable,
                    retry_delay_seconds=retry_delay,
                    delivery_ambiguous=exc.delivery_ambiguous,
                )
            except Exception:
                failed += 1
                await self._safe_fail(
                    job,
                    "provider_unexpected",
                    True,
                    self._retry_delay(job.attempt_count),
                )
            else:
                completion_started_at = time.monotonic()
                try:
                    await self._repository.complete(
                        job.id, self._worker_id, result.message_id
                    )
                except asyncio.CancelledError as exc:
                    self._log_ambiguous_completion(
                        job=job,
                        provider_message_id=result.message_id,
                        error=exc,
                        completion_result="cancelled",
                        started_at=completion_started_at,
                    )
                    raise
                except Exception as exc:
                    ambiguous += 1
                    self._log_ambiguous_completion(
                        job=job,
                        provider_message_id=result.message_id,
                        error=exc,
                        completion_result="failed",
                        started_at=completion_started_at,
                    )
                else:
                    sent += 1
                    log_event(
                        logger,
                        "notification.delivery_sent",
                        "Notification delivery completed",
                        component="notification-worker",
                        notification_event_id=job.id,
                        channel=job.channel,
                        provider_message_id=result.message_id,
                        attempt_number=job.attempt_count,
                    )
        return WorkerRunResult(
            claimed=len(jobs),
            sent=sent,
            failed=failed,
            ambiguous=ambiguous,
        )

    def _log_ambiguous_completion(
        self,
        *,
        job: OutboxJob,
        provider_message_id: str,
        error: BaseException,
        completion_result: Literal["cancelled", "failed"],
        started_at: float,
    ) -> None:
        duration_ms = max(0, round((time.monotonic() - started_at) * 1_000))
        log_event(
            logger,
            "notification.delivery_completion_ambiguous",
            "Provider accepted notification but durable completion is ambiguous",
            level="WARNING",
            component="notification-worker",
            notification_event_id=job.id,
            provider_message_id=provider_message_id,
            idempotency_key=job.provider_idempotency_key,
            attempt_number=job.attempt_count,
            previous_state="processing",
            requested_state="sent",
            completion_result=completion_result,
            reconciliation_status="required",
            error_class=type(error).__name__,
            duration_ms=duration_ms,
        )

    async def _safe_fail(
        self,
        job: OutboxJob,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
    ) -> None:
        try:
            await self._repository.fail(
                job.id,
                self._worker_id,
                error_class,
                retryable,
                retry_delay_seconds,
            )
        except Exception as exc:
            logger.warning(
                "notification outbox failure transition failed",
                extra={"error_type": type(exc).__name__},
            )

    @staticmethod
    def _log_delivery_failure(
        *,
        job: OutboxJob,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
        delivery_ambiguous: bool,
    ) -> None:
        event = (
            "notification.delivery_retry_scheduled"
            if retryable
            else "notification.delivery_failed"
        )
        log_event(
            logger,
            event,
            (
                "Notification delivery retry scheduled"
                if retryable
                else "Notification delivery failed"
            ),
            level="WARNING" if not retryable else "INFO",
            component="notification-worker",
            notification_event_id=job.id,
            channel=job.channel,
            error_class=error_class,
            attempt_number=job.attempt_count,
            retryable=retryable,
            retry_delay_seconds=retry_delay_seconds,
            delivery_ambiguous=delivery_ambiguous,
        )

    def _retry_delay(self, attempt_count: int) -> int:
        exponent = max(0, attempt_count - 1)
        base = min(
            self._base_retry_seconds * (2**exponent),
            self._max_retry_seconds,
        )
        jitter_max = min(self._base_retry_seconds, self._max_retry_seconds - base)
        return base + self._jitter(0, max(0, jitter_max))
