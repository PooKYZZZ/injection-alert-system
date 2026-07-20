import pytest

from web_app.domain.enforcement import (
    POLICY_VERSION,
    EnforcementPolicy,
    EnforcementScope,
    EnforcementTier,
    RecommendedAction,
)


@pytest.mark.parametrize(
    ("prediction", "tier", "expected_action"),
    [
        ("SQL Injection", "LOW", RecommendedAction.MONITOR),
        ("Other Attacks", "MEDIUM", RecommendedAction.THROTTLE),
        ("Code Injection", "HIGH", RecommendedAction.APPLICATION_BLOCK),
        ("SQL Injection", "CRITICAL", RecommendedAction.WAF_BLOCK),
    ],
)
def test_non_normal_predictions_map_to_shadow_policy_intent(
    prediction: str,
    tier: str,
    expected_action: RecommendedAction,
) -> None:
    recommendation = EnforcementPolicy.recommend(
        prediction=prediction,
        confidence_level=tier,
        request_path="/records/search",
    )

    assert recommendation is not None
    assert recommendation.scope is EnforcementScope.RECORD_SEARCH
    assert recommendation.tier.value == tier
    assert recommendation.action is expected_action
    assert recommendation.policy_version == POLICY_VERSION


@pytest.mark.parametrize("tier", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_normal_prediction_produces_no_recommendation(tier: str) -> None:
    assert (
        EnforcementPolicy.recommend(
            prediction="Normal",
            confidence_level=tier,
            request_path="/records/search",
        )
        is None
    )


def test_unsupported_path_produces_no_recommendation() -> None:
    assert (
        EnforcementPolicy.recommend(
            prediction="SQL Injection",
            confidence_level="HIGH",
            request_path="/support/submit",
        )
        is None
    )


@pytest.mark.parametrize(
    ("prediction", "confidence_level"),
    [("", "HIGH"), ("SQL Injection", "UNKNOWN"), ("SQL Injection", "")],
)
def test_invalid_policy_input_fails_closed(
    prediction: str,
    confidence_level: str,
) -> None:
    with pytest.raises(ValueError):
        EnforcementPolicy.recommend(
            prediction=prediction,
            confidence_level=confidence_level,
            request_path="/records/search",
        )


def test_policy_recommendation_is_immutable() -> None:
    recommendation = EnforcementPolicy.recommend(
        prediction="SQL Injection",
        confidence_level="HIGH",
        request_path="/records/search",
    )

    assert recommendation is not None
    with pytest.raises((AttributeError, TypeError)):
        recommendation.action = RecommendedAction.WAF_BLOCK  # type: ignore[misc]
