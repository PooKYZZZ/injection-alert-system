import asyncio

import pytest

from web_app.application.inference_queue import (
    InferenceQueueFullError,
    InferenceQueueService,
)
from web_app.config import Settings


def _settings(maxsize: int) -> Settings:
    return Settings(
        env_file=False,
        database_url="sqlite+aiosqlite://",
        model_path="unused",
        model_registry_path="unused",
        inference_queue_maxsize=maxsize,
    )


@pytest.mark.asyncio
async def test_queue_initializes_with_configured_max_size():
    service = InferenceQueueService(_settings(3))
    await service.start()
    try:
        assert service.health()["max_size"] == 3
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_submit_returns_coroutine_result():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        result = await service.submit(lambda: _successful_job("ok"))
    finally:
        await service.stop()

    assert result == "ok"


@pytest.mark.asyncio
async def test_submit_starts_worker_when_not_running():
    service = InferenceQueueService(_settings(2))
    try:
        result = await service.submit(lambda: _successful_job("ok"))
    finally:
        await service.stop()

    assert result == "ok"


@pytest.mark.asyncio
async def test_successful_job_increments_enqueued_and_processed_counts():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        await service.submit(lambda: _successful_job("ok"))
        health = service.health()
    finally:
        await service.stop()

    assert health["total_enqueued"] == 1
    assert health["total_processed"] == 1


@pytest.mark.asyncio
async def test_full_queue_raises_inference_queue_full_error():
    service = InferenceQueueService(_settings(1))
    started = asyncio.Event()
    release = asyncio.Event()
    running_task = None
    queued_task = None
    try:
        await service.start()
        running_task = asyncio.create_task(
            service.submit(lambda: _blocking_job(started, release, "running"))
        )
        await started.wait()
        queued_task = asyncio.create_task(service.submit(lambda: _successful_job("queued")))
        await _wait_for_queue_depth(service, 1)

        with pytest.raises(InferenceQueueFullError):
            await service.submit(lambda: _successful_job("overflow"))
    finally:
        release.set()
        if queued_task is not None:
            await queued_task
        if running_task is not None:
            await running_task
        await service.stop()


@pytest.mark.asyncio
async def test_overflow_count_increments_on_each_overflow_attempt():
    service = InferenceQueueService(_settings(1))
    started = asyncio.Event()
    release = asyncio.Event()
    running_task = None
    queued_task = None
    try:
        await service.start()
        running_task = asyncio.create_task(
            service.submit(lambda: _blocking_job(started, release, "running"))
        )
        await started.wait()
        queued_task = asyncio.create_task(service.submit(lambda: _successful_job("queued")))
        await _wait_for_queue_depth(service, 1)

        for _ in range(2):
            with pytest.raises(InferenceQueueFullError):
                await service.submit(lambda: _successful_job("overflow"))
    finally:
        health = service.health()
        release.set()
        if queued_task is not None:
            await queued_task
        if running_task is not None:
            await running_task
        await service.stop()

    assert health["overflow_count"] == 2


@pytest.mark.asyncio
async def test_failed_job_increments_total_failed():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        with pytest.raises(ValueError):
            await service.submit(lambda: _failed_job("boom"))
        health = service.health()
    finally:
        await service.stop()

    assert health["total_failed"] == 1


@pytest.mark.asyncio
async def test_failed_job_exception_propagates_to_submit_call_site():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        with pytest.raises(RuntimeError, match="job failed"):
            await service.submit(lambda: _runtime_failed_job())
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_cancelled_job_propagates_without_stopping_worker():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        with pytest.raises(asyncio.CancelledError):
            await service.submit(lambda: _cancelled_job())

        assert service.health()["worker_running"] is True
        assert service.health()["total_failed"] == 1
        result = await service.submit(lambda: _successful_job("ok"))
    finally:
        await service.stop()

    assert result == "ok"


@pytest.mark.asyncio
async def test_last_error_is_set_and_truncated_after_failure():
    service = InferenceQueueService(_settings(2))
    await service.start()
    try:
        with pytest.raises(ValueError):
            await service.submit(lambda: _failed_job("x" * 250))
        health = service.health()
    finally:
        await service.stop()

    assert health["last_error"] is not None
    assert len(health["last_error"]) <= 200
    assert health["last_error_at"] is not None


@pytest.mark.asyncio
async def test_last_error_redacts_secret_like_exception_messages():
    for message in (
        "Bearer secret-token",
        "Cookie: session=secret",
        "api_key=abc123",
        "postgresql://user:password@db.example/app",
    ):
        service = InferenceQueueService(_settings(2))
        await service.start()
        try:
            with pytest.raises(ValueError):
                await service.submit(lambda message=message: _failed_job(message))
            health = service.health()
        finally:
            await service.stop()

        assert health["last_error"] == "[redacted]"
        assert "secret" not in health["last_error"]


@pytest.mark.asyncio
async def test_stop_cancels_worker_cleanly_without_hanging():
    service = InferenceQueueService(_settings(2))
    await service.start()

    await asyncio.wait_for(service.stop(), timeout=1)

    assert service.health()["worker_running"] is False


@pytest.mark.asyncio
async def test_stop_cancels_running_and_pending_submitters_without_hanging():
    service = InferenceQueueService(_settings(1))
    started = asyncio.Event()
    release = asyncio.Event()
    await service.start()
    running_task = asyncio.create_task(
        service.submit(lambda: _blocking_job(started, release, "running"))
    )
    await started.wait()
    queued_task = asyncio.create_task(service.submit(lambda: _successful_job("queued")))
    await _wait_for_queue_depth(service, 1)

    await asyncio.wait_for(service.stop(), timeout=1)
    results = await asyncio.gather(
        running_task,
        queued_task,
        return_exceptions=True,
    )

    assert all(isinstance(result, asyncio.CancelledError) for result in results)


async def _successful_job(value: str) -> str:
    await asyncio.sleep(0)
    return value


async def _blocking_job(
    started: asyncio.Event,
    release: asyncio.Event,
    value: str,
) -> str:
    started.set()
    await release.wait()
    return value


async def _failed_job(message: str) -> None:
    await asyncio.sleep(0)
    raise ValueError(message)


async def _runtime_failed_job() -> None:
    await asyncio.sleep(0)
    raise RuntimeError("job failed")


async def _cancelled_job() -> None:
    await asyncio.sleep(0)
    raise asyncio.CancelledError()


async def _wait_for_queue_depth(
    service: InferenceQueueService,
    expected_depth: int,
) -> None:
    for _ in range(100):
        if service.health()["depth"] == expected_depth:
            return
        await asyncio.sleep(0)
    raise AssertionError(f"queue depth did not reach {expected_depth}")
