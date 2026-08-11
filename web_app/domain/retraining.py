"""Retraining domain records shared by the application and ML boundaries."""

from web_app.domain.interfaces import (
    RetrainingReviewCandidate,
    RetrainingReviewSummary,
)

__all__ = ["RetrainingReviewCandidate", "RetrainingReviewSummary"]
