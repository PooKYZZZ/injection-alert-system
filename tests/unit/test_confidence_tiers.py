import pytest


def test_shared_confidence_classifier_boundary_values():
    try:
        from ml_model.confidence_tiers import ConfidenceThresholds, classify_confidence
    except ModuleNotFoundError as exc:
        pytest.fail(f"shared confidence classifier module is missing: {exc}")

    thresholds = ConfidenceThresholds(low=0.50, high=0.80, critical=0.90)

    assert classify_confidence(0.49, thresholds=thresholds) == "LOW"
    assert classify_confidence(0.50, thresholds=thresholds) == "MEDIUM"
    assert classify_confidence(0.80, thresholds=thresholds) == "MEDIUM"
    assert classify_confidence(0.800001, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.899999, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.8999999999999999, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.90, thresholds=thresholds) == "CRITICAL"
    assert classify_confidence(1.0, thresholds=thresholds) == "CRITICAL"


def test_shared_confidence_classifier_rejects_invalid_confidence():
    try:
        from ml_model.confidence_tiers import ConfidenceThresholds, classify_confidence
    except ModuleNotFoundError as exc:
        pytest.fail(f"shared confidence classifier module is missing: {exc}")

    thresholds = ConfidenceThresholds(low=0.50, high=0.80, critical=0.90)

    with pytest.raises(ValueError):
        classify_confidence(-0.01, thresholds=thresholds)

    with pytest.raises(ValueError):
        classify_confidence(1.01, thresholds=thresholds)
