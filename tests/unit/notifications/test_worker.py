from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

import pytest

from web_app.notifications.models import OutboxJob, ProviderSendResult
from web_app.notifications.providers import EmailProviderError
from web_app.notifications.worker import OutboxWorker


def job(*, attempt_count: int = 1) -> OutboxJob:
    return OutboxJob(
        id="00000000-0000-0000-0000-000000000001",
        kind="threat_detected",
        recipient="soc@example.test",
        safe_payload={
            "event_id": "alert-42",
            "timestamp": "2026-07-10T09:00:00Z",
            "attack_category": "SQL Injection",
            "confidence_tier": "HIGH",
            "action_taken": "BLOCKED",
            "route_path": "/records/search",
            "dashboard_url": "https://dashboard.example.test/alerts/42",
        },
        template_version=1,
        dedupe_key="threat/alert-42",
        provider_idempotency_key="threat/alert-42",
        attempt_count=attempt_count,
        max_attempts=5,
    )


@dataclass
class RepositoryStub:
    jobs: list[OutboxJob]
    completed: list[tuple[str, str, str]] = field(default_factory=list)
    failed: list[tuple[str, str, str, bool, int]] = field(default_factory=list)

    async def claim_batch(self, worker_id: str, batch_size: int, lease_seconds: int):
        return self.jobs

    async def complete(self, job_id: str, worker_id: str, message_id: str):
        self.completed.append((job_id, worker_id, message_id))

    async def fail(
        self,
        job_id: str,
        worker_id: str,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
    ):
        self.failed.append(
            (job_id, worker_id, error_class, retryable, retry_delay_seconds)
        )


class SuccessfulProvider:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return ProviderSendResult(message_id="provider-1")


class FailingProvider:
    async def send(self, _message):
        raise EmailProviderError("rate_limit_exceeded", retryable=True)


@dataclass
class TransitionFailureRepository(RepositoryStub):
    fail_transitions: bool = False
    complete_transitions: bool = False

    async def complete(self, job_id: str, worker_id: str, message_id: str):
        if self.complete_transitions:
            raise RuntimeError("lost completion lease")
        await super().complete(job_id, worker_id, message_id)

    async def fail(
        self,
        job_id: str,
        worker_id: str,
        error_class: str,
        retryable: bool,
        retry_delay_seconds: int,
    ):
        if self.fail_transitions:
            raise RuntimeError("lost failure lease")
        await super().fail(
            job_id, worker_id, error_class, retryable, retry_delay_seconds
        )


@pytest.mark.asyncio
async def test_worker_completes_claimed_job() -> None:
    repository = RepositoryStub([job()])
    provider = SuccessfulProvider()
    worker = OutboxWorker(
        repository=repository,
        provider=provider,
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    result = await worker.run_once()

    assert result.claimed == 1
    assert result.sent == 1
    assert result.failed == 0
    assert repository.completed == [
        (job().id, "worker-a", "provider-1")
    ]
    assert repository.failed == []


@pytest.mark.asyncio
async def test_worker_records_retry_without_raising_or_mutating_job_contract() -> None:
    claimed = job(attempt_count=2)
    repository = RepositoryStub([claimed])
    worker = OutboxWorker(
        repository=repository,
        provider=FailingProvider(),
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    result = await worker.run_once()

    assert result.claimed == 1
    assert result.sent == 0
    assert result.failed == 1
    assert repository.completed == []
    assert repository.failed == [
        (claimed.id, "worker-a", "rate_limit_exceeded", True, 60)
    ]
    assert claimed.provider_idempotency_key == "threat/alert-42"
    assert claimed.safe_payload["event_id"] == "alert-42"


@pytest.mark.asyncio
async def test_worker_survives_lost_transition_and_continues_processing() -> None:
    repository = TransitionFailureRepository(
        [job(), job()], complete_transitions=True
    )
    provider = SuccessfulProvider()
    worker = OutboxWorker(
        repository=repository,
        provider=provider,
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    result = await worker.run_once()

    assert result == type(result)(claimed=2, sent=2, failed=0)
    assert len(provider.messages) == 2


@pytest.mark.asyncio
async def test_worker_does_not_render_after_deadline() -> None:
    expired = job()
    expired = replace(
        expired,
        deliver_before=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    repository = RepositoryStub([expired])
    provider = SuccessfulProvider()
    worker = OutboxWorker(
        repository=repository,
        provider=provider,
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    result = await worker.run_once()

    assert result.claimed == 1
    assert result.sent == 0
    assert result.failed == 1
    assert provider.messages == []
    assert repository.failed[0][2] == "delivery_deadline_expired"
