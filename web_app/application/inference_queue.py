from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

from web_app.config import Settings


class InferenceQueueFullError(RuntimeError):
    """Raised when the inference queue has no available capacity."""


class InferenceQueueService:
    """Bounded in-process queue that gates async inference work."""

    _SENSITIVE_PATTERNS = (
        "authorization",
        "bearer ",
        "cookie",
        "token=",
        "password=",
        "secret",
        "key",
        "://",
    )
    def __init__(self, settings: Settings):
        self._max_size = settings.inference_queue_maxsize
        self._queue: asyncio.Queue[
            tuple[asyncio.Future[Any], Callable[[], Coroutine[Any, Any, Any]]]
        ] = asyncio.Queue(maxsize=self._max_size)
        self._worker_task: asyncio.Task[None] | None = None
        self._total_enqueued = 0
        self._total_processed = 0
        self._total_failed = 0
        self._overflow_count = 0
        self._last_error: str | None = None
        self._last_error_at: str | None = None
        self._last_processed_at: str | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._run_worker())

    async def stop(self) -> None:
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        while True:
            try:
                future, _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not future.done():
                future.set_exception(asyncio.CancelledError())
            self._queue.task_done()

    async def submit(
        self,
        coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    ) -> Any:
        if self._worker_task is None or self._worker_task.done():
            await self.start()

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        try:
            self._queue.put_nowait((future, coro_factory))
        except asyncio.QueueFull as exc:
            self._overflow_count += 1
            raise InferenceQueueFullError("Inference queue is full") from exc

        self._total_enqueued += 1
        return await future

    def health(self) -> dict[str, object]:
        depth = self._queue.qsize()
        return {
            "enabled": True,
            "max_size": self._max_size,
            "depth": depth,
            "available_capacity": self._max_size - depth,
            "worker_count": 1,
            "worker_running": self._worker_task is not None
            and not self._worker_task.done(),
            "total_enqueued": self._total_enqueued,
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "overflow_count": self._overflow_count,
            "last_error": self._last_error,
            "last_error_at": self._last_error_at,
            "last_processed_at": self._last_processed_at,
        }

    async def _run_worker(self) -> None:
        while True:
            future, coro_factory = await self._queue.get()
            try:
                result = await coro_factory()
            except asyncio.CancelledError as exc:
                if not future.done():
                    future.set_exception(exc)
                current_task = asyncio.current_task()
                if current_task is not None and current_task.cancelling():
                    raise
                self._total_failed += 1
                self._last_error = self._sanitize_error(exc)
                self._last_error_at = self._utc_now()
            except Exception as exc:
                self._total_failed += 1
                self._last_error = self._sanitize_error(exc)
                self._last_error_at = self._utc_now()
                if not future.done():
                    future.set_exception(exc)
            else:
                self._total_processed += 1
                self._last_processed_at = self._utc_now()
                if not future.done():
                    future.set_result(result)
            finally:
                self._queue.task_done()

    def _sanitize_error(self, exc: Exception) -> str:
        raw = str(exc)
        raw_lower = raw.lower()
        if any(pattern in raw_lower for pattern in self._SENSITIVE_PATTERNS):
            return "[redacted]"
        return raw[:200]

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
