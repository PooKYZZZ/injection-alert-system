from datetime import datetime

import pytest

from web_app.application.label_review_use_case import (
    InvalidLabelReviewError,
    LabelReviewUseCase,
    ReviewerContext,
    UnauthorizedLabelReviewerError,
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
        reviewer_id="owner-1",
        reviewer_role="OWNER",
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
        reviewer=ReviewerContext("owner-1", "OWNER"),
    )

    assert result.review.id == 1
    assert repository.arguments["reviewer_id"] == "owner-1"
    assert repository.arguments["reviewer_role"] == "OWNER"
    assert isinstance(repository.arguments["reviewed_at"], datetime)


@pytest.mark.asyncio
async def test_invalid_label_state_identity_and_note_are_rejected():
    repository = RecordingRepository(_review())
    common = {
        "alert_id": 10,
        "verified_label": "Normal",
        "approval_state": "approved_for_training",
        "reviewer": ReviewerContext("owner-1", "OWNER"),
    }
    for override in [
        {"verified_label": "free-form"},
        {"approval_state": "superseded"},
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
        reviewer=ReviewerContext("owner-1", "OWNER"),
    )
    assert result is None


@pytest.mark.parametrize("role", ["ADMIN", "ANALYST", "VIEWER"])
@pytest.mark.asyncio
async def test_non_owner_cannot_submit_label_review(role):
    repository = RecordingRepository(_review())

    with pytest.raises(UnauthorizedLabelReviewerError):
        await LabelReviewUseCase(repository).execute(
            alert_id=10,
            verified_label="Normal",
            approval_state="approved_for_training",
            reviewer=ReviewerContext(f"{role.lower()}-1", role),
        )

    assert repository.arguments is None
