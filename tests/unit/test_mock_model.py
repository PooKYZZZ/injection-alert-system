import pytest
from ml_model.models.mock_model import MockInjectionClassifier, ConfidenceLevel


def test_mock_model_predicts_sql_injection():
    """Test that SQL injection patterns are detected"""
    model = MockInjectionClassifier()
    result = model.predict("SELECT * FROM users WHERE id = 1 OR 1=1")
    assert result["class"] == "SQL Injection"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_mock_model_predicts_code_injection():
    """Test that code injection patterns are detected"""
    model = MockInjectionClassifier()
    result = model.predict("<script>alert('XSS')</script>")
    assert result["class"] == "Code Injection"
    assert 0.0 <= result["confidence"] <= 1.0


def test_mock_model_predicts_normal_request():
    """Test that normal requests are classified correctly"""
    model = MockInjectionClassifier()
    result = model.predict("GET /api/users?page=1&limit=10")
    assert result["class"] == "Normal"
    assert result["confidence"] > 0.8  # High confidence for normal


def test_mock_model_confidence_levels():
    """Test confidence level thresholds"""
    model = MockInjectionClassifier()
    # HIGH confidence (> 0.8)
    high_result = model.predict("SELECT * FROM users; DROP TABLE users;--")
    assert high_result["confidence_level"] == "HIGH"
    assert high_result["confidence"] > 0.8

    # Test that confidence level matches confidence value
    result = model.predict("UNION SELECT password FROM admin")
    if result["confidence"] < 0.5:
        assert result["confidence_level"] == "LOW"
    elif result["confidence"] <= 0.8:
        assert result["confidence_level"] == "MEDIUM"
    else:
        assert result["confidence_level"] == "HIGH"


def test_mock_model_other_attacks():
    """Test detection of other attack types"""
    model = MockInjectionClassifier()
    result = model.predict("../../../etc/passwd")
    assert result["class"] == "Other Attacks"


def test_mock_model_empty_input():
    """Test handling of empty input"""
    model = MockInjectionClassifier()
    result = model.predict("")
    assert result["class"] == "Normal"
    assert result["confidence"] >= 0.0
