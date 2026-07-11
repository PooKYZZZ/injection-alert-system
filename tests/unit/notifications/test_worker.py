from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

import pytest

from web_app.notifications.models import OutboxJob, ProviderSendResult
from web_app.notifications.providers import EmailProviderError
from web_app.notifications.worker import OutboxWorker
from web_app.observability.context import reset_request_context, set_request_context


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
    assert result.ambiguous == 0
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
    assert result.ambiguous == 0
    assert repository.completed == []
    assert repository.failed == [
        (claimed.id, "worker-a", "rate_limit_exceeded", True, 60)
    ]
    assert claimed.provider_idempotency_key == "threat/alert-42"
    assert claimed.safe_payload["event_id"] == "alert-42"


@pytest.mark.asyncio
async def test_worker_records_provider_accepted_completion_failure_as_ambiguous(
    caplog,
) -> None:
    secret_bearing_job = replace(
        job(),
        kind="password_reset",
        safe_payload={
            "reset_url": "https://dashboard.example.test/reset?token=raw-secret",
        },
    )
    repository = TransitionFailureRepository(
        [secret_bearing_job, secret_bearing_job], complete_transitions=True
    )
    provider = SuccessfulProvider()
    worker = OutboxWorker(
        repository=repository,
        provider=provider,
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    tokens = set_request_context(
        request_id="notification-request-1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    )
    try:
        with caplog.at_level(logging.WARNING):
            result = await worker.run_once()
    finally:
        reset_request_context(tokens)

    assert result == type(result)(claimed=2, sent=0, failed=0, ambiguous=2)
    assert len(provider.messages) == 2
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]
    assert len(events) == 2
    expected_fields = {
        "event": "notification.delivery_completion_ambiguous",
        "notification_event_id": job().id,
        "request_id": "notification-request-1",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "provider_message_id": "provider-1",
        "idempotency_key": "threat/alert-42",
        "attempt_number": 1,
        "previous_state": "processing",
        "requested_state": "sent",
        "completion_result": "failed",
        "reconciliation_status": "required",
        "error_class": "RuntimeError",
    }
    assert {key: events[0][key] for key in expected_fields} == expected_fields
    assert isinstance(events[0]["duration_ms"], int)
    assert "soc@example.test" not in caplog.text
    assert "dashboard.example.test" not in caplog.text
    assert "raw-secret" not in caplog.text


@pytest.mark.asyncio
async def test_worker_retries_ambiguous_completion_with_same_idempotency_key() -> None:
    @dataclass
    class CompleteOnSecondAttemptRepository(RepositoryStub):
        completion_attempts: int = 0

        async def complete(self, job_id: str, worker_id: str, message_id: str):
            self.completion_attempts += 1
            if self.completion_attempts == 1:
                raise RuntimeError("completion unavailable")
            await super().complete(job_id, worker_id, message_id)

    repository = CompleteOnSecondAttemptRepository([job()])
    provider = SuccessfulProvider()
    worker = OutboxWorker(
        repository=repository,
        provider=provider,
        worker_id="worker-a",
        jitter=lambda _low, _high: 0,
    )

    first = await worker.run_once()
    second = await worker.run_once()

    assert first == type(first)(claimed=1, sent=0, failed=0, ambiguous=1)
    assert second == type(second)(claimed=1, sent=1, failed=0, ambiguous=0)
    assert [message.idempotency_key for message in provider.messages] == [
        "threat/alert-42",
        "threat/alert-42",
    ]


@pytest.mark.asyncio
async def test_worker_shutdown_after_provider_acceptance_is_logged_and_propagated(
    caplog,
) -> None:
    @dataclass
    class CancelledCompletionRepository(RepositoryStub):
        async def complete(self, _job_id: str, _worker_id: str, _message_id: str):
            raise asyncio.CancelledError

    worker = OutboxWorker(
        repository=CancelledCompletionRepository([job()]),
        provider=SuccessfulProvider(),
        worker_id="worker-a",
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_once()

    event = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    )
    assert event["completion_result"] == "cancelled"
    assert event["reconciliation_status"] == "required"


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
    assert result.ambiguous == 0
    assert provider.messages == []
    assert repository.failed[0][2] == "delivery_deadline_expired"
