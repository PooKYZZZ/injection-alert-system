from __future__ import annotations

import random
from typing import Callable, Protocol

from web_app.notifications.models import OutboxJob, WorkerRunResult
from web_app.notifications.providers import EmailProvider, EmailProviderError
from web_app.notifications.templates import TemplatePayloadError, render_email


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
        batch_size: int = 10,
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
        for job in jobs:
            try:
                message = render_email(
                    kind=job.kind,
                    recipient=job.recipient,
                    payload=job.safe_payload,
                    template_version=job.template_version,
                    idempotency_key=job.provider_idempotency_key,
                )
                result = await self._provider.send(message)
            except TemplatePayloadError:
                failed += 1
                await self._repository.fail(
                    job.id,
                    self._worker_id,
                    "template_payload_invalid",
                    False,
                    0,
                )
            except EmailProviderError as exc:
                failed += 1
                await self._repository.fail(
                    job.id,
                    self._worker_id,
                    exc.error_class,
                    exc.retryable,
                    self._retry_delay(job.attempt_count) if exc.retryable else 0,
                )
            except Exception:
                failed += 1
                await self._repository.fail(
                    job.id,
                    self._worker_id,
                    "provider_unexpected",
                    True,
                    self._retry_delay(job.attempt_count),
                )
            else:
                sent += 1
                await self._repository.complete(
                    job.id, self._worker_id, result.message_id
                )
        return WorkerRunResult(claimed=len(jobs), sent=sent, failed=failed)

    def _retry_delay(self, attempt_count: int) -> int:
        exponent = max(0, attempt_count - 1)
        base = min(
            self._base_retry_seconds * (2**exponent),
            self._max_retry_seconds,
        )
        jitter_max = min(self._base_retry_seconds, self._max_retry_seconds - base)
        return base + self._jitter(0, max(0, jitter_max))
