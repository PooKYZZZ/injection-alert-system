"""Unit tests for TriageUseCase.

These tests use mock objects for both the classifier and repository,
verifying that the use case correctly:
  1. Calls the classifier with the HTTP request
  2. Applies the correct confidence-gated action logic
  3. Persists the entity through the repository interface
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from web_app.application.triage_use_case import TriageUseCase, TriageResult
from web_app.domain.interfaces import TrafficLogEntity


@pytest.fixture
def mock_classifier():
    """Create a mock classifier."""
    classifier = MagicMock()
    return classifier


@pytest.fixture
def mock_repository():
    """Create a mock repository with async save."""
    repo = AsyncMock()
    repo.save.return_value = TrafficLogEntity(
        id=1,
        source_ip="127.0.0.1",
        http_request="test",
        prediction="Normal",
        confidence=0.9,
        confidence_level="HIGH",
        action_taken="ALLOWED",
    )
    return repo


@pytest.mark.asyncio
async def test_triage_high_confidence_attack_is_blocked(mock_classifier, mock_repository):
    """HIGH confidence + non-Normal class → BLOCKED"""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.95,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="SELECT * FROM users; DROP TABLE users;--",
        source_ip="192.168.1.1",
    )

    assert result.class_label == "SQL Injection"
    assert result.action_taken == "BLOCKED"
    assert result.confidence == 0.95
    mock_classifier.predict.assert_called_once()
    mock_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_triage_medium_confidence_is_throttled(mock_classifier, mock_repository):
    """MEDIUM confidence → THROTTLED regardless of class"""
    mock_classifier.predict.return_value = {
        "class": "Code Injection",
        "confidence": 0.65,
        "confidence_level": "MEDIUM",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="<script>alert(1)</script>",
        source_ip="10.0.0.1",
    )

    assert result.action_taken == "THROTTLED"
    mock_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_triage_normal_high_confidence_is_allowed(mock_classifier, mock_repository):
    """HIGH confidence + Normal class → ALLOWED (not BLOCKED)"""
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.95,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="GET /index.html",
        source_ip="127.0.0.1",
    )

    assert result.class_label == "Normal"
    assert result.action_taken == "ALLOWED"


@pytest.mark.asyncio
async def test_triage_low_confidence_is_allowed(mock_classifier, mock_repository):
    """LOW confidence → ALLOWED"""
    mock_classifier.predict.return_value = {
        "class": "Other Attacks",
        "confidence": 0.3,
        "confidence_level": "LOW",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="GET /api/data",
        source_ip="10.0.0.1",
    )

    assert result.action_taken == "ALLOWED"


@pytest.mark.asyncio
async def test_triage_persists_correct_entity_fields(mock_classifier, mock_repository):
    """Verify the entity passed to repository.save has the correct fields."""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.88,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    await use_case.execute(
        http_request="UNION SELECT password FROM admin",
        source_ip="192.168.1.100",
    )

    # Verify the entity passed to save
    saved_entity = mock_repository.save.call_args[0][0]
    assert isinstance(saved_entity, TrafficLogEntity)
    assert saved_entity.source_ip == "192.168.1.100"
    assert saved_entity.http_request == "UNION SELECT password FROM admin"
    assert saved_entity.prediction == "SQL Injection"
    assert saved_entity.confidence == 0.88
    assert saved_entity.action_taken == "BLOCKED"
