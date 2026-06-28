"""
Unit tests for AlertQueryParams schema validation.

Tests cover:
- Default values
- Valid filter values
- Invalid values rejected by Pydantic
- Filter combinations
"""

import pytest
from pydantic import ValidationError

from web_app.presentation.schemas.schemas import AlertQueryParams


class TestAlertQueryParams:
    """Test cases for AlertQueryParams schema validation."""

    def test_default_params(self):
        """Test default query parameters."""
        params = AlertQueryParams()

        assert params.page == 1
        assert params.page_size == 20
        assert params.severity is None
        assert params.confidence_tier is None
        assert params.time_range is None
        assert params.search is None
        assert params.action is None
        assert params.triage_status is None
        assert params.confidence_level is None
        assert params.prediction is None
        assert params.source_ip is None
        assert params.sort_by == "timestamp"
        assert params.sort_dir == "desc"

    def test_valid_severity_filter(self):
        """Test valid severity filter values."""
        for severity in ["ALL", "LOW", "MEDIUM", "HIGH"]:
            params = AlertQueryParams(severity=severity)
            assert params.severity == severity

    def test_valid_confidence_tier_filter(self):
        """Test valid confidence_tier filter values."""
        for confidence_tier in ["ALL", "LOW", "MEDIUM", "HIGH"]:
            params = AlertQueryParams(confidence_tier=confidence_tier)
            assert params.confidence_tier == confidence_tier

    def test_valid_time_range_filter(self):
        """Test valid time_range filter values."""
        for time_range in ["1h", "6h", "24h", "7d"]:
            params = AlertQueryParams(time_range=time_range)
            assert params.time_range == time_range

    def test_valid_action_filter(self):
        """Test valid action filter values."""
        for action in ["BLOCKED", "THROTTLED", "ALLOWED"]:
            params = AlertQueryParams(action=action)
            assert params.action == action

    def test_valid_triage_status_filter(self):
        """Test valid triage_status filter values."""
        for status in ["new", "in_review", "escalated", "resolved", "false_positive"]:
            params = AlertQueryParams(triage_status=status)
            assert params.triage_status == status

    def test_valid_prediction_filter(self):
        """Test valid prediction filter values."""
        for prediction in [
            "SQL Injection",
            "Code Injection",
            "Other Attacks",
            "Normal",
        ]:
            params = AlertQueryParams(prediction=prediction)
            assert params.prediction == prediction

    def test_valid_confidence_level_filter(self):
        """Test valid confidence_level filter values."""
        params = AlertQueryParams(confidence_level=["HIGH", "MEDIUM"])
        assert params.confidence_level == ["HIGH", "MEDIUM"]

    def test_valid_pagination_params(self):
        """Test valid pagination parameters."""
        params = AlertQueryParams(page=5, page_size=50)
        assert params.page == 5
        assert params.page_size == 50

    def test_valid_sort_params(self):
        """Test valid sorting parameters."""
        params = AlertQueryParams(sort_by="confidence", sort_dir="asc")
        assert params.sort_by == "confidence"
        assert params.sort_dir == "asc"


class TestAlertQueryParamsCombinations:
    """Test cases for filter combinations in AlertQueryParams."""

    def test_severity_and_action_combination(self):
        """Test combining severity and action filters."""
        params = AlertQueryParams(
            severity="HIGH",
            action="BLOCKED",
        )
        assert params.severity == "HIGH"
        assert params.action == "BLOCKED"

    def test_matching_severity_and_confidence_tier_combination(self):
        """Test matching legacy and preferred confidence-tier filters."""
        params = AlertQueryParams(
            severity="HIGH",
            confidence_tier="HIGH",
        )
        assert params.severity == "HIGH"
        assert params.confidence_tier == "HIGH"

    def test_time_range_and_triage_status_combination(self):
        """Test combining time_range and triage_status filters."""
        params = AlertQueryParams(
            time_range="24h",
            triage_status="new",
        )
        assert params.time_range == "24h"
        assert params.triage_status == "new"

    def test_confidence_level_and_prediction_combination(self):
        """Test combining confidence_level and prediction filters."""
        params = AlertQueryParams(
            confidence_level=["HIGH", "MEDIUM"],
            prediction="SQL Injection",
        )
        assert params.confidence_level == ["HIGH", "MEDIUM"]
        assert params.prediction == "SQL Injection"

    def test_all_filters_combined(self):
        """Test all filters combined together."""
        params = AlertQueryParams(
            page=2,
            page_size=50,
            severity="HIGH",
            time_range="6h",
            search="injection",
            action="BLOCKED",
            triage_status="in_review",
            confidence_level=["HIGH", "MEDIUM"],
            prediction="SQL Injection",
            source_ip="10.0.0.1",
            sort_by="action",
            sort_dir="desc",
        )
        assert params.page == 2
        assert params.page_size == 50
        assert params.severity == "HIGH"
        assert params.time_range == "6h"
        assert params.search == "injection"
        assert params.action == "BLOCKED"
        assert params.triage_status == "in_review"
        assert params.confidence_level == ["HIGH", "MEDIUM"]
        assert params.prediction == "SQL Injection"
        assert params.source_ip == "10.0.0.1"
        assert params.sort_by == "action"
        assert params.sort_dir == "desc"

    def test_all_sort_by_values(self):
        """Test all valid sort_by values."""
        for sort_by in [
            "timestamp",
            "confidence",
            "severity",
            "confidence_tier",
            "action",
        ]:
            params = AlertQueryParams(sort_by=sort_by)
            assert params.sort_by == sort_by

    def test_all_sort_dir_values(self):
        """Test all valid sort_dir values."""
        for sort_dir in ["asc", "desc"]:
            params = AlertQueryParams(sort_dir=sort_dir)
            assert params.sort_dir == sort_dir


class TestAlertQueryParamsEdgeCases:
    """Test edge cases for AlertQueryParams."""

    def test_empty_search_string(self):
        """Test empty search string is allowed."""
        params = AlertQueryParams(search="")
        assert params.search == ""

    def test_conflicting_severity_and_confidence_tier_raises(self):
        """Test conflicting legacy and preferred filters are rejected."""
        params = AlertQueryParams(severity="LOW", confidence_tier="HIGH")
        with pytest.raises(ValueError, match="severity and confidence_tier"):
            params.ensure_compatible_confidence_tier_aliases()

    def test_none_values_for_optional_fields(self):
        """Test None values for optional fields."""
        params = AlertQueryParams(
            severity=None,
            confidence_tier=None,
            time_range=None,
            search=None,
            action=None,
            triage_status=None,
            confidence_level=None,
            prediction=None,
            source_ip=None,
        )
        assert params.severity is None
        assert params.confidence_tier is None
        assert params.time_range is None

    def test_page_below_minimum_raises(self):
        """Test page below minimum raises ValidationError."""
        with pytest.raises(ValidationError):
            AlertQueryParams(page=0)

    def test_page_size_above_maximum_raises(self):
        """Test page_size above maximum raises ValidationError."""
        with pytest.raises(ValidationError):
            AlertQueryParams(page_size=200)

    def test_page_size_below_minimum_raises(self):
        """Test page_size below minimum raises ValidationError."""
        with pytest.raises(ValidationError):
            AlertQueryParams(page_size=0)

    def test_page_minimum_valid(self):
        """Test page=1 is accepted."""
        params = AlertQueryParams(page=1)
        assert params.page == 1

    def test_page_size_maximum_valid(self):
        """Test page_size=100 is accepted."""
        params = AlertQueryParams(page_size=100)
        assert params.page_size == 100
