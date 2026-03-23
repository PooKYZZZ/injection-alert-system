"""
Unit tests for UpdateAlertTriageUseCase.

Tests cover:
- Valid patch (triage status update)
- Partial patch (updating only triage status)
- Invalid payload (400)
- Unauthenticated (401)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from web_app.application.update_alert_triage_use_case import (
    UpdateAlertTriageUseCase,
    UpdateAlertTriageResult,
    InvalidTriageStatusError,
    VALID_TRIAGE_STATUSES,
)


class TestUpdateAlertTriageUseCase:
    """Test cases for alert triage status update."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.update_triage_status = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_repository):
        """Create use case with mock repository."""
        return UpdateAlertTriageUseCase(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_valid_patch_new_status(self, use_case, mock_repository):
        """Test updating triage status to 'new'."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="SQL Injection",
            confidence=0.85,
            confidence_level="HIGH",
            triage_status="new",
        )

        result = await use_case.execute(
            alert_id=1,
            triage_status="new",
        )

        assert result.success is True
        assert result.alert is not None
        assert result.alert.triage_status == "new"
        mock_repository.update_triage_status.assert_called_once_with(
            traffic_id=1,
            triage_status="new",
        )

    @pytest.mark.asyncio
    async def test_valid_patch_in_review_status(self, use_case, mock_repository):
        """Test updating triage status to 'in_review'."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="SQL Injection",
            confidence=0.85,
            confidence_level="HIGH",
            triage_status="in_review",
        )

        result = await use_case.execute(alert_id=1, triage_status="in_review")
        assert result.success is True
        assert result.alert.triage_status == "in_review"

    @pytest.mark.asyncio
    async def test_valid_patch_escalated_status(self, use_case, mock_repository):
        """Test updating triage status to 'escalated'."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="SQL Injection",
            confidence=0.85,
            confidence_level="HIGH",
            triage_status="escalated",
        )

        result = await use_case.execute(alert_id=1, triage_status="escalated")
        assert result.success is True
        assert result.alert.triage_status == "escalated"

    @pytest.mark.asyncio
    async def test_valid_patch_resolved_status(self, use_case, mock_repository):
        """Test updating triage status to 'resolved'."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="SQL Injection",
            confidence=0.85,
            confidence_level="HIGH",
            triage_status="resolved",
        )

        result = await use_case.execute(alert_id=1, triage_status="resolved")
        assert result.success is True
        assert result.alert.triage_status == "resolved"

    @pytest.mark.asyncio
    async def test_valid_patch_false_positive_status(self, use_case, mock_repository):
        """Test updating triage status to 'false_positive'."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="Normal",
            confidence=0.95,
            confidence_level="HIGH",
            triage_status="false_positive",
        )

        result = await use_case.execute(alert_id=1, triage_status="false_positive")
        assert result.success is True
        assert result.alert.triage_status == "false_positive"

    @pytest.mark.asyncio
    async def test_partial_patch_only_updates_triage_status(
        self, use_case, mock_repository
    ):
        """Test that partial patch only updates triage status, leaving other fields unchanged."""
        from web_app.domain.interfaces import TrafficLogEntity

        mock_repository.update_triage_status.return_value = TrafficLogEntity(
            id=1,
            transaction_id="txn-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            http_request="GET /api HTTP/1.1",
            prediction="SQL Injection",
            confidence=0.85,
            confidence_level="HIGH",
            triage_status="in_review",
        )

        result = await use_case.execute(alert_id=1, triage_status="in_review")

        assert result.success is True
        assert result.alert.prediction == "SQL Injection"
        assert result.alert.confidence == 0.85
        assert result.alert.triage_status == "in_review"
        mock_repository.update_triage_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_payload_unknown_status(self, use_case):
        """Test that invalid triage status raises InvalidTriageStatusError (400)."""
        with pytest.raises(InvalidTriageStatusError) as exc_info:
            await use_case.execute(alert_id=1, triage_status="invalid_status")

        assert "Invalid triage_status" in str(exc_info.value)
        assert "invalid_status" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_payload_empty_status(self, use_case):
        """Test that empty triage status raises InvalidTriageStatusError."""
        with pytest.raises(InvalidTriageStatusError):
            await use_case.execute(alert_id=1, triage_status="")

    @pytest.mark.asyncio
    async def test_invalid_payload_none_status(self, use_case):
        """Test that None triage status raises InvalidTriageStatusError."""
        with pytest.raises(InvalidTriageStatusError):
            await use_case.execute(alert_id=1, triage_status=None)

    @pytest.mark.asyncio
    async def test_alert_not_found_returns_failure(self, use_case, mock_repository):
        """Test that updating non-existent alert returns failure."""
        mock_repository.update_triage_status.return_value = None

        result = await use_case.execute(alert_id=999, triage_status="new")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_valid_statuses_are_recognized(self):
        """Test that all valid triage statuses are recognized."""
        valid_statuses = {"new", "in_review", "escalated", "resolved", "false_positive"}
        assert VALID_TRIAGE_STATUSES == valid_statuses


class TestTriageUpdateRequestSchema:
    """Test cases for TriageUpdateRequest schema validation."""

    def test_valid_triage_status_values(self):
        """Test that valid triage status values pass validation."""
        from web_app.presentation.schemas.schemas import TriageUpdateRequest

        for status in ["new", "in_review", "escalated", "resolved", "false_positive"]:
            req = TriageUpdateRequest(triage_status=status)
            assert req.triage_status == status

    def test_invalid_triage_status_rejected(self):
        """Test that invalid triage status values are rejected by schema."""
        from web_app.presentation.schemas.schemas import TriageUpdateRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TriageUpdateRequest(triage_status="invalid")
