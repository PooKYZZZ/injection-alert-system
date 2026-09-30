import math

import pytest

from ml_model.confidence_tiers import ConfidenceThresholds, classify_confidence


def test_shared_confidence_classifier_boundary_values():
    thresholds = ConfidenceThresholds()

    assert classify_confidence(0.0, thresholds=thresholds) == "INFORMATIONAL"
    assert classify_confidence(math.nextafter(0.0, 1.0), thresholds=thresholds) == "LOW"
    assert classify_confidence(0.3899, thresholds=thresholds) == "LOW"
    assert classify_confidence(0.39, thresholds=thresholds) == "LOW"
    assert classify_confidence(0.3999, thresholds=thresholds) == "LOW"
    assert classify_confidence(0.40, thresholds=thresholds) == "MEDIUM"
    assert classify_confidence(0.69, thresholds=thresholds) == "MEDIUM"
    assert classify_confidence(0.6999, thresholds=thresholds) == "MEDIUM"
    assert classify_confidence(0.70, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.89, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.8999, thresholds=thresholds) == "HIGH"
    assert classify_confidence(0.90, thresholds=thresholds) == "CRITICAL"
    assert classify_confidence(1.0, thresholds=thresholds) == "CRITICAL"


def test_shared_confidence_classifier_rejects_invalid_confidence():
    thresholds = ConfidenceThresholds()

    with pytest.raises(ValueError):
        classify_confidence(-0.01, thresholds=thresholds)

    with pytest.raises(ValueError):
        classify_confidence(1.01, thresholds=thresholds)

    with pytest.raises(ValueError):
        classify_confidence(float("nan"), thresholds=thresholds)
