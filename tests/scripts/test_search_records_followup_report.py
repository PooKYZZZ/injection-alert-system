from scripts.search_records_followup_report import (
    _confidence_counts,
    _label_counts,
    _mutation_summary,
)


def _row(
    *,
    mutation: str,
    predicted: str,
    correct: str,
    confidence_level: str,
) -> dict[str, str]:
    return {
        "mutation": mutation,
        "predicted_label": predicted,
        "classification_correct": correct,
        "confidence_level": confidence_level,
    }


def test_followup_summary_preserves_label_confidence_and_mutation_breakdowns() -> None:
    rows = [
        _row(
            mutation="wrapper_variation",
            predicted="Code Injection",
            correct="True",
            confidence_level="HIGH",
        ),
        _row(
            mutation="wrapper_variation",
            predicted="Other Attacks",
            correct="False",
            confidence_level="MEDIUM",
        ),
        _row(
            mutation="case_variation",
            predicted="SQL Injection",
            correct="False",
            confidence_level="CRITICAL",
        ),
    ]
    assert _label_counts(rows) == {
        "Code Injection": 1,
        "Other Attacks": 1,
        "SQL Injection": 1,
    }
    assert _confidence_counts(rows) == {
        "CRITICAL": 1,
        "HIGH": 1,
        "MEDIUM": 1,
    }
    summary = _mutation_summary(rows)
    assert summary["wrapper_variation"]["tested"] == 2
    assert summary["wrapper_variation"]["correct"] == 1
    assert summary["case_variation"]["accuracy_percent"] == 0.0
