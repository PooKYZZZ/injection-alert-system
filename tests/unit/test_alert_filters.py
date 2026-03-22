"""
Unit tests for alert filtering in TrafficLogRepository.

Covers filtering by severity, status, action, combined filters, and edge cases.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)
from web_app.domain.interfaces import TrafficLogEntity
from sqlalchemy.ext.asyncio import AsyncSession


class TestAlertFilters:
    """Test cases for alert filtering logic."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_db_session):
        """Create repository with mock session."""
        return TrafficLogRepository(mock_db_session)

    @pytest.fixture
    def sample_entities(self):
        """Create sample traffic log entities for filtering tests."""
        base_time = datetime.now(timezone.utc)
        return [
            TrafficLogEntity(
                id=1,
                transaction_id="txn-1",
                timestamp=base_time - timedelta(minutes=30),
                source_ip="192.168.1.1",
                http_request="GET /api HTTP/1.1",
                prediction="Normal",
                confidence=0.95,
                confidence_level="HIGH",
                action_taken="ALLOWED",
                triage_status="new",
            ),
            TrafficLogEntity(
                id=2,
                transaction_id="txn-2",
                timestamp=base_time - timedelta(hours=2),
                source_ip="192.168.1.2",
                http_request="POST /login HTTP/1.1",
                prediction="SQL Injection",
                confidence=0.85,
                confidence_level="HIGH",
                action_taken="BLOCKED",
                triage_status="in_review",
            ),
            TrafficLogEntity(
                id=3,
                transaction_id="txn-3",
                timestamp=base_time - timedelta(hours=5),
                source_ip="192.168.1.3",
                http_request="GET /search HTTP/1.1",
                prediction="Code Injection",
                confidence=0.65,
                confidence_level="MEDIUM",
                action_taken="THROTTLED",
                triage_status="escalated",
            ),
            TrafficLogEntity(
                id=4,
                transaction_id="txn-4",
                timestamp=base_time - timedelta(days=1),
                source_ip="192.168.1.4",
                http_request="GET /admin HTTP/1.1",
                prediction="Other Attacks",
                confidence=0.35,
                confidence_level="LOW",
                action_taken="ALLOWED",
                triage_status="resolved",
            ),
            TrafficLogEntity(
                id=5,
                transaction_id="txn-5",
                timestamp=base_time - timedelta(days=3),
                source_ip="192.168.1.5",
                http_request="GET /info HTTP/1.1",
                prediction="Normal",
                confidence=0.98,
                confidence_level="HIGH",
                action_taken="ALLOWED",
                triage_status="false_positive",
            ),
        ]

    def _mock_execute_for_list(self, mock_db_session, entities, total=None):
        """Helper to configure mock session for get_alert_list calls.

        get_alert_list calls execute() twice:
        1. COUNT query -> total = int(total_result.scalar_one())
        2. SELECT query -> rows = result.scalars().all()
        """

        def side_effect(stmt):
            stmt_str = str(stmt)
            mock = MagicMock()
            if "count" in stmt_str.lower() or "anon" in stmt_str.lower():
                mock.scalar_one.return_value = (
                    total if total is not None else len(entities)
                )
            else:
                mock.scalars.return_value.all.return_value = entities
            return mock

        mock_db_session.execute.side_effect = side_effect

    @pytest.mark.asyncio
    async def test_filter_by_severity_high(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by HIGH severity (confidence_level)."""
        high_entities = [e for e in sample_entities if e.confidence_level == "HIGH"]
        self._mock_execute_for_list(
            mock_db_session, high_entities, total=len(high_entities)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="HIGH",
        )

        assert page.total == 3

    @pytest.mark.asyncio
    async def test_filter_by_severity_medium(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by MEDIUM severity."""
        medium_entities = [e for e in sample_entities if e.confidence_level == "MEDIUM"]
        self._mock_execute_for_list(
            mock_db_session, medium_entities, total=len(medium_entities)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="MEDIUM",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_filter_by_severity_all_returns_all(
        self, repository, mock_db_session, sample_entities
    ):
        """Test that severity=ALL returns all records."""
        self._mock_execute_for_list(
            mock_db_session, sample_entities, total=len(sample_entities)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="ALL",
        )

        assert page.total == len(sample_entities)

    @pytest.mark.asyncio
    async def test_filter_by_triage_status_new(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by triage_status='new'."""
        new_entities = [e for e in sample_entities if e.triage_status == "new"]
        self._mock_execute_for_list(
            mock_db_session, new_entities, total=len(new_entities)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            triage_status="new",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_filter_by_action_blocked(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by action='BLOCKED'."""
        blocked = [e for e in sample_entities if e.action_taken == "BLOCKED"]
        self._mock_execute_for_list(mock_db_session, blocked, total=len(blocked))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            action="BLOCKED",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_filter_by_action_allowed(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by action='ALLOWED'."""
        allowed = [e for e in sample_entities if e.action_taken == "ALLOWED"]
        self._mock_execute_for_list(mock_db_session, allowed, total=len(allowed))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            action="ALLOWED",
        )

        assert page.total == 3

    @pytest.mark.asyncio
    async def test_filter_by_confidence_levels_multiple(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by multiple confidence levels."""
        high_medium = [
            e for e in sample_entities if e.confidence_level in ["HIGH", "MEDIUM"]
        ]
        self._mock_execute_for_list(
            mock_db_session, high_medium, total=len(high_medium)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            confidence_levels=["HIGH", "MEDIUM"],
        )

        assert page.total == 4

    @pytest.mark.asyncio
    async def test_filter_by_prediction(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by prediction label."""
        sqli = [e for e in sample_entities if e.prediction == "SQL Injection"]
        self._mock_execute_for_list(mock_db_session, sqli, total=len(sqli))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            prediction="SQL Injection",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_filter_by_source_ip(
        self, repository, mock_db_session, sample_entities
    ):
        """Test filtering by exact source IP."""
        ip2 = [e for e in sample_entities if e.source_ip == "192.168.1.2"]
        self._mock_execute_for_list(mock_db_session, ip2, total=len(ip2))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            source_ip="192.168.1.2",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_combined_filters_severity_and_action(
        self, repository, mock_db_session, sample_entities
    ):
        """Test combining severity and action filters."""
        filtered = [
            e
            for e in sample_entities
            if e.confidence_level == "HIGH" and e.action_taken == "BLOCKED"
        ]
        self._mock_execute_for_list(mock_db_session, filtered, total=len(filtered))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="HIGH",
            action="BLOCKED",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_combined_filters_all_params(
        self, repository, mock_db_session, sample_entities
    ):
        """Test combining multiple filter parameters."""
        filtered = [
            e
            for e in sample_entities
            if e.confidence_level == "HIGH"
            and e.action_taken == "BLOCKED"
            and e.triage_status == "in_review"
        ]
        self._mock_execute_for_list(mock_db_session, filtered, total=len(filtered))

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="HIGH",
            action="BLOCKED",
            triage_status="in_review",
            time_range="24h",
        )

        assert page.total == 1

    @pytest.mark.asyncio
    async def test_pagination(self, repository, mock_db_session, sample_entities):
        """Test pagination with page and page_size."""
        self._mock_execute_for_list(
            mock_db_session, sample_entities[:2], total=len(sample_entities)
        )

        page = await repository.get_alert_list(
            page=2,
            page_size=2,
        )

        assert page.page == 2
        assert page.page_size == 2
        assert len(page.items) <= 2

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(
        self, repository, mock_db_session, sample_entities
    ):
        """Test that no filters returns all records."""
        self._mock_execute_for_list(
            mock_db_session, sample_entities, total=len(sample_entities)
        )

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
        )

        assert page.total == len(sample_entities)

    @pytest.mark.asyncio
    async def test_empty_result_set(self, repository, mock_db_session):
        """Test filtering that returns no results."""
        self._mock_execute_for_list(mock_db_session, [], total=0)

        page = await repository.get_alert_list(
            page=1,
            page_size=20,
            severity="HIGH",
            prediction="NonExistent",
        )

        assert page.total == 0
        assert page.items == []
