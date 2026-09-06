import pytest

from web_app.domain.classification_scope import (
    ClassificationScope,
    classification_scope,
    is_actionable_attack_class,
    is_operational_traffic_class,
)


@pytest.mark.parametrize(
    ("prediction", "scope", "actionable", "operational"),
    [
        ("Normal", ClassificationScope.BENIGN, False, True),
        ("SQL Injection", ClassificationScope.IN_SCOPE, True, True),
        ("Code Injection", ClassificationScope.IN_SCOPE, True, True),
        ("Other Attacks", ClassificationScope.OUT_OF_SCOPE, False, False),
        ("Future Attack", ClassificationScope.OUT_OF_SCOPE, False, False),
        (None, ClassificationScope.OUT_OF_SCOPE, False, False),
    ],
)
def test_classification_scope_is_explicit_and_fail_closed(
    prediction: str | None,
    scope: ClassificationScope,
    actionable: bool,
    operational: bool,
) -> None:
    assert classification_scope(prediction) is scope
    assert is_actionable_attack_class(prediction) is actionable
    assert is_operational_traffic_class(prediction) is operational
