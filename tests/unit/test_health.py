from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import Response

from web_app.presentation import health as health_module


@dataclass
class SettingsStub:
    notification_worker_enabled: bool
    notification_worker_required: bool


@dataclass
class WorkerStub:
    running: bool = True
    last_poll_at: float | None = 1.0
    last_error_class: str | None = None


class DatabaseStub:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails

    async def execute(self, _statement):
        if self.fails:
            raise RuntimeError("database unavailable")
        return self

    def first(self):
        return None


class RequestStub:
    def __init__(self, worker=None) -> None:
        self.app = type("App", (), {})()
        self.app.state = type("State", (), {})()
        self.app.state.notification_worker = worker


@pytest.mark.asyncio
async def test_required_unhealthy_worker_fails_readiness(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_settings",
        lambda: SettingsStub(True, True),
    )
    response = Response()

    result = await health_module.health_check(
        RequestStub(WorkerStub(last_error_class="RuntimeError")),
        response,
        DatabaseStub(),
    )

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "connected"
    assert result.notification_worker == "unhealthy"


@pytest.mark.asyncio
async def test_optional_unhealthy_worker_is_reported_without_failing_readiness(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        health_module,
        "get_settings",
        lambda: SettingsStub(True, False),
    )
    response = Response()

    result = await health_module.health_check(
        RequestStub(WorkerStub(last_error_class="RuntimeError")),
        response,
        DatabaseStub(),
    )

    assert response.status_code == 200
    assert result.status == "healthy"
    assert result.notification_worker == "unhealthy"


@pytest.mark.asyncio
async def test_disabled_optional_worker_does_not_fail_readiness(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_settings",
        lambda: SettingsStub(False, False),
    )
    response = Response()

    result = await health_module.health_check(
        RequestStub(),
        response,
        DatabaseStub(),
    )

    assert response.status_code == 200
    assert result.status == "healthy"
    assert result.notification_worker == "disabled"


@pytest.mark.asyncio
async def test_database_failure_fails_readiness(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_settings",
        lambda: SettingsStub(False, False),
    )
    response = Response()

    result = await health_module.health_check(
        RequestStub(),
        response,
        DatabaseStub(fails=True),
    )

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "disconnected"
