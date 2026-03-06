"""Unit tests for FeedbackUseCase.

Tests use a mock repository to verify feedback recording logic
without touching the database.
"""

import pytest
from unittest.mock import AsyncMock

from web_app.application.feedback_use_case import FeedbackUseCase
from web_app.domain.interfaces import TrafficLogEntity


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_feedback_success(mock_repository):
    """Test successful feedback recording."""
    mock_repository.update_feedback.return_value = TrafficLogEntity(
        id=1,
        http_request="test",
        prediction="SQL Injection",
        confidence=0.9,
        confidence_level="HIGH",
        analyst_label="False Positive",
        labeled_by="analyst@example.com",
    )

    use_case = FeedbackUseCase(repository=mock_repository)
    result = await use_case.execute(
        traffic_id=1,
        correct_label="False Positive",
        analyst_email="analyst@example.com",
    )

    assert result.success is True
    assert result.traffic_id == 1
    assert "successfully" in result.message.lower()
    mock_repository.update_feedback.assert_called_once()


@pytest.mark.asyncio
async def test_feedback_not_found(mock_repository):
    """Test feedback on non-existent traffic log."""
    mock_repository.update_feedback.return_value = None

    use_case = FeedbackUseCase(repository=mock_repository)
    result = await use_case.execute(
        traffic_id=999,
        correct_label="Normal",
        analyst_email="analyst@example.com",
    )

    assert result.success is False
    assert result.traffic_id == 999
    assert "not found" in result.message.lower()
