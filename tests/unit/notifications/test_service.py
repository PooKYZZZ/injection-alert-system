from __future__ import annotations

from dataclasses import dataclass

import pytest

from web_app.notifications.providers import FakeEmailProvider
from web_app.notifications.service import NotificationWorkerService


@dataclass
class WorkerSettings:
    notification_worker_enabled: bool = True
    notification_worker_poll_seconds: float = 0.01
    notification_worker_batch_size: int = 10
    notification_worker_lease_seconds: int = 60


class EmptyRepository:
    def __init__(self) -> None:
        self.claims = 0

    async def claim_batch(self, _worker_id, _batch_size, _lease_seconds):
        self.claims += 1
        return []

    async def complete(self, *_args):
        raise AssertionError("No job should complete.")

    async def fail(self, *_args):
        raise AssertionError("No job should fail.")


@dataclass
class RequiredSettings(WorkerSettings):
    notification_worker_required: bool = True


@pytest.mark.asyncio
async def test_notification_service_runs_and_stops_cleanly() -> None:
    repository = EmptyRepository()
    service = NotificationWorkerService(
        settings=WorkerSettings(),
        repository=repository,
        provider=FakeEmailProvider(),
        worker_id="worker-test",
    )

    await service.start()
    await service.wait_until_polled()
    await service.stop()

    assert repository.claims >= 1
    assert service.running is False


@pytest.mark.asyncio
async def test_notification_service_stays_disabled_by_default() -> None:
    repository = EmptyRepository()
    service = NotificationWorkerService(
        settings=WorkerSettings(notification_worker_enabled=False),
        repository=repository,
        provider=FakeEmailProvider(),
        worker_id="worker-test",
    )

    await service.start()

    assert service.running is False
    assert repository.claims == 0


@pytest.mark.asyncio
async def test_required_worker_performs_a_startup_probe() -> None:
    repository = EmptyRepository()
    service = NotificationWorkerService(
        settings=RequiredSettings(),
        repository=repository,
        provider=FakeEmailProvider(),
        worker_id="worker-test",
    )

    await service.start()
    await service.stop()

    assert repository.claims >= 1
    assert service.last_poll_at is not None
