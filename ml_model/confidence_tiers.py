from dataclasses import dataclass
from typing import Literal

ConfidenceTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class ConfidenceThresholds:
    low: float = 0.50
    high: float = 0.80
    critical: float = 0.90

    def __post_init__(self) -> None:
        if not 0.0 <= self.low < self.high < self.critical <= 1.0:
            raise ValueError(
                "confidence thresholds must satisfy 0.0 <= low < high < critical <= 1.0"
            )


DEFAULT_CONFIDENCE_THRESHOLDS = ConfidenceThresholds()


def classify_confidence(
    confidence: float,
    *,
    thresholds: ConfidenceThresholds = DEFAULT_CONFIDENCE_THRESHOLDS,
) -> ConfidenceTier:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be within 0.0..1.0")

    if confidence < thresholds.low:
        return "LOW"
    if confidence <= thresholds.high:
        return "MEDIUM"
    if confidence < thresholds.critical:
        return "HIGH"
    return "CRITICAL"
