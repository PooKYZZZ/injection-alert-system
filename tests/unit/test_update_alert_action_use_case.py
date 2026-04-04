"""Unit tests for UpdateAlertActionUseCase."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from web_app.application.update_alert_action_use_case import (
    InvalidAlertActionError,
    UpdateAlertActionUseCase,
)
from web_app.domain.interfaces import TrafficLogEntity


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.update_action_taken = AsyncMock()
    return repo


@pytest.fixture
def use_case(mock_repository):
    return UpdateAlertActionUseCase(repository=mock_repository)


@pytest.mark.asyncio
async def test_execute_updates_action_taken_entity(mock_repository, use_case):
    mock_repository.update_action_taken.return_value = TrafficLogEntity(
        id=1,
        transaction_id="txn-1",
        timestamp=datetime.now(timezone.utc),
        source_ip="192.168.1.1",
        http_request="GET /api HTTP/1.1",
        prediction="SQL Injection",
        confidence=0.88,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )

    result = await use_case.execute(alert_id=1, action_taken="BLOCKED")

    assert result.success is True
    assert result.alert is not None
    assert result.alert.action_taken == "BLOCKED"
    mock_repository.update_action_taken.assert_called_once_with(
        traffic_id=1,
        action_taken="BLOCKED",
    )


@pytest.mark.asyncio
async def test_execute_raises_for_invalid_action(use_case):
    with pytest.raises(InvalidAlertActionError):
        await use_case.execute(alert_id=1, action_taken="INVALID")


@pytest.mark.asyncio
async def test_execute_returns_not_found_result_when_alert_missing(mock_repository, use_case):
    mock_repository.update_action_taken.return_value = None

    result = await use_case.execute(alert_id=999, action_taken="THROTTLED")

    assert result.success is False
    assert "not found" in result.message.lower()
