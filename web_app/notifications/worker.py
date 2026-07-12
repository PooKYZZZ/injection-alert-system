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
from web_app.notifications.providers import EmailProvider, EmailProviderError
from web_app.notifications.templates import TemplatePayloadError, render_email
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
        provider: EmailProvider,
        worker_id: str,
        batch_size: int = 1,
        lease_seconds: int = 60,
        base_retry_seconds: int = 30,
        max_retry_seconds: int = 3_600,
        jitter: Callable[[int, int], int] = random.randint,
    ) -> None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("Worker id is invalid.")
        self._repository = repository
        self._provider = provider
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
                message = render_email(
                    kind=job.kind,
                    recipient=job.recipient,
                    payload=payload,
                    template_version=job.template_version,
                    idempotency_key=job.provider_idempotency_key,
                )
                result = await self._provider.send(message)
            except NotificationPayloadError:
                failed += 1
                await self._safe_fail(job, "payload_decryption_failed", False, 0)
            except TemplatePayloadError:
                failed += 1
                await self._safe_fail(job, "template_payload_invalid", False, 0)
            except EmailProviderError as exc:
                failed += 1
                await self._safe_fail(
                    job,
                    exc.error_class,
                    exc.retryable,
                    self._retry_delay(job.attempt_count) if exc.retryable else 0,
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

    def _retry_delay(self, attempt_count: int) -> int:
        exponent = max(0, attempt_count - 1)
        base = min(
            self._base_retry_seconds * (2**exponent),
            self._max_retry_seconds,
        )
        jitter_max = min(self._base_retry_seconds, self._max_retry_seconds - base)
        return base + self._jitter(0, max(0, jitter_max))
