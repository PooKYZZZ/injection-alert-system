from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from contextlib import suppress
from typing import Protocol
from uuid import uuid4

from web_app.notifications.outbox import PostgresNotificationOutboxRepository
from web_app.notifications.providers import (
    EmailProvider,
    FakeEmailProvider,
    ResendEmailProvider,
)
from web_app.notifications.worker import OutboxRepository, OutboxWorker

logger = logging.getLogger(__name__)


class WorkerSettings(Protocol):
    notification_worker_enabled: bool
    notification_worker_poll_seconds: float
    notification_worker_batch_size: int
    notification_worker_lease_seconds: int


class ProviderSettings(WorkerSettings, Protocol):
    email_provider: str
    resend_api_key: str | None
    resend_from_email: str


def build_email_provider(settings: ProviderSettings) -> EmailProvider:
    if settings.email_provider == "fake":
        return FakeEmailProvider()
    if settings.email_provider == "resend":
        if not settings.resend_api_key or not settings.resend_from_email:
            raise RuntimeError("Resend provider configuration is incomplete.")
        return ResendEmailProvider(
            api_key=settings.resend_api_key,
            from_email=settings.resend_from_email,
        )
    raise RuntimeError("Email provider configuration is invalid.")


class NotificationWorkerService:
    def __init__(
        self,
        *,
        settings: WorkerSettings,
        repository: OutboxRepository,
        provider: EmailProvider,
        worker_id: str,
    ) -> None:
        self._settings = settings
        self._worker = OutboxWorker(
            repository=repository,
            provider=provider,
            worker_id=worker_id,
            batch_size=settings.notification_worker_batch_size,
            lease_seconds=settings.notification_worker_lease_seconds,
        )
        self._stop = asyncio.Event()
        self._polled = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._last_poll_at: float | None = None
        self._last_error_class: str | None = None
        self._last_sent = 0
        self._last_failed = 0
        self._last_ambiguous = 0

    @classmethod
    def from_settings(cls, settings: ProviderSettings) -> "NotificationWorkerService":
        from web_app.infrastructure.database import database as db_module

        worker_id = (
            f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:12]}"
        )[:128]
        return cls(
            settings=settings,
            repository=PostgresNotificationOutboxRepository(
                db_module.AsyncSessionLocal
            ),
            provider=build_email_provider(settings),
            worker_id=worker_id,
        )

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self._settings.notification_worker_enabled or self.running:
            return
        self._stop.clear()
        self._polled.clear()
        if getattr(self._settings, "notification_worker_required", False):
            result = await self._worker.run_once()
            self._last_sent = result.sent
            self._last_failed = result.failed
            self._last_ambiguous = result.ambiguous
            self._last_poll_at = time.time()
        self._task = asyncio.create_task(
            self._run(), name="notification-outbox-worker"
        )

    async def stop(self) -> None:
        if self._task is not None:
            self._stop.set()
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        close = getattr(self._worker._provider, "close", None)
        if close is not None:
            await close()

    async def wait_until_polled(self) -> None:
        await asyncio.wait_for(self._polled.wait(), timeout=2.0)

    @property
    def last_poll_at(self) -> float | None:
        return self._last_poll_at

    @property
    def last_error_class(self) -> str | None:
        return self._last_error_class

    @property
    def last_sent(self) -> int:
        return self._last_sent

    @property
    def last_failed(self) -> int:
        return self._last_failed

    @property
    def last_ambiguous(self) -> int:
        return self._last_ambiguous

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                result = await self._worker.run_once()
                self._last_sent = result.sent
                self._last_failed = result.failed
                self._last_ambiguous = result.ambiguous
                self._last_error_class = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error_class = type(exc).__name__
                logger.error(
                    "notification worker poll failed",
                    extra={"error_type": type(exc).__name__},
                )
            finally:
                self._last_poll_at = time.time()
                self._polled.set()
            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._settings.notification_worker_poll_seconds,
                )
            except TimeoutError:
                continue
