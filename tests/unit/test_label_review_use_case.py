from datetime import datetime

import pytest

from web_app.application.label_review_use_case import (
    InvalidLabelReviewError,
    LabelReviewUseCase,
    ReviewerContext,
)
from web_app.domain.interfaces import TrafficLabelReview


class RecordingRepository:
    def __init__(self, review=None):
        self.review = review
        self.arguments = None

    async def create_review_revision(self, **kwargs):
        self.arguments = kwargs
        return self.review


def _review() -> TrafficLabelReview:
    return TrafficLabelReview(
        id=1,
        traffic_log_id=10,
        revision=1,
        predicted_label="SQL Injection",
        verified_label="Normal",
        approval_state="approved_for_training",
        reviewer_id="analyst-1",
        reviewer_role="ANALYST",
        reviewed_at=datetime.now(),
        model_version="model-v1",
        input_hash="a" * 64,
        review_note=None,
    )


@pytest.mark.asyncio
async def test_valid_review_uses_authenticated_reviewer_context():
    repository = RecordingRepository(_review())
    result = await LabelReviewUseCase(repository).execute(
        alert_id=10,
        verified_label="Normal",
        approval_state="approved_for_training",
        reviewer=ReviewerContext("analyst-1", "ANALYST"),
    )

    assert result.review.id == 1
    assert repository.arguments["reviewer_id"] == "analyst-1"
    assert repository.arguments["reviewer_role"] == "ANALYST"
    assert isinstance(repository.arguments["reviewed_at"], datetime)


@pytest.mark.asyncio
async def test_invalid_label_state_identity_and_note_are_rejected():
    repository = RecordingRepository(_review())
    common = {
        "alert_id": 10,
        "verified_label": "Normal",
        "approval_state": "approved_for_training",
        "reviewer": ReviewerContext("analyst-1", "ANALYST"),
    }
    for override in [
        {"verified_label": "free-form"},
        {"approval_state": "superseded"},
        {"reviewer": ReviewerContext("viewer-1", "VIEWER")},
        {"review_note": "x" * 1001},
    ]:
        with pytest.raises(InvalidLabelReviewError):
            await LabelReviewUseCase(repository).execute(**{**common, **override})


@pytest.mark.asyncio
async def test_unknown_alert_returns_none():
    repository = RecordingRepository(None)
    result = await LabelReviewUseCase(repository).execute(
        alert_id=999,
        verified_label="Normal",
        approval_state="excluded_from_training",
        reviewer=ReviewerContext("analyst-1", "ANALYST"),
    )
    assert result is None
