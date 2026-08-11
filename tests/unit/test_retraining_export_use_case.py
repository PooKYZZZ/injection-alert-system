from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from web_app.application.retraining_export_use_case import (
    RetrainingExportUseCase,
)
from web_app.domain.retraining import (
    RetrainingReviewCandidate,
    RetrainingReviewSummary,
)

RUN_ID = "retrain-20260810T120000Z-000000000001"


def _candidate(
    traffic_log_id: int,
    *,
    revision: int = 1,
    approval_state: str = "approved_for_training",
    label: str = "SQL Injection",
    text: str | None = None,
    reviewer_id: str = "analyst-1",
    preprocessing_version: str = MODEL_INPUT_VERSION,
) -> RetrainingReviewCandidate:
    model_input_text = text or f"get /records/{traffic_log_id}"
    return RetrainingReviewCandidate(
        review_id=traffic_log_id * 10 + revision,
        traffic_log_id=traffic_log_id,
        revision=revision,
        predicted_label="SQL Injection",
        verified_label=label,
        approval_state=approval_state,
        reviewer_id=reviewer_id,
        reviewer_role="ANALYST",
        reviewed_at=datetime(2026, 8, 10, 12, traffic_log_id, tzinfo=timezone.utc),
        model_version="active-v1",
        prediction_confidence=0.98,
        prediction_confidence_level="HIGH",
        model_input_hash=sha256(model_input_text.encode()).hexdigest(),
        model_input_text=model_input_text,
        preprocessing_version=preprocessing_version,
        ingest_event_hash="a" * 64,
        source_verification_status="UNVERIFIED",
        source_provenance="DIRECT_REMOTE_ADDR",
    )


class FakeReviewRepository:
    def __init__(self, candidates):
        self.candidates = list(candidates)

    async def list_latest_retraining_candidates(self, *, limit: int):
        return self.candidates[:limit]

    async def get_retraining_review_summary(self):
        return RetrainingReviewSummary(
            approved=sum(
                candidate.approval_state == "approved_for_training"
                for candidate in self.candidates
            ),
            excluded=sum(
                candidate.approval_state == "excluded_from_training"
                for candidate in self.candidates
            ),
            unreviewed=0,
        )


@pytest.mark.asyncio
async def test_export_uses_latest_approved_rows_and_does_not_consume_them(tmp_path):
    repository = FakeReviewRepository(
        [_candidate(1), _candidate(2, approval_state="excluded_from_training")]
    )
    use_case = RetrainingExportUseCase(repository, output_root=tmp_path)

    first = await use_case.execute(run_id=RUN_ID)

    assert first.status == "READY"
    assert [sample.traffic_log_id for sample in first.samples] == [1]
    assert first.manifest["rejected_counts"]["EXCLUDED_FROM_TRAINING"] == 1
    assert "get /records/1" not in first.manifest.__repr__()

    repository.candidates.append(_candidate(3, label="Normal"))
    second = await use_case.execute(run_id="retrain-20260810T120001Z-000000000002")

    assert [sample.traffic_log_id for sample in second.samples] == [1, 3]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (_candidate(1, text="tampered"), "HASH_MISMATCH"),
        (
            _candidate(1, preprocessing_version="unknown-v9"),
            "UNSUPPORTED_PREPROCESSING",
        ),
        (_candidate(1, reviewer_id=""), "UNTRUSTED_REVIEWER"),
    ],
)
async def test_export_rejects_invalid_training_evidence(tmp_path, candidate, reason):
    if reason == "HASH_MISMATCH":
        candidate = replace(candidate, model_input_hash="f" * 64)
    repository = FakeReviewRepository([candidate])
    result = await RetrainingExportUseCase(repository, output_root=tmp_path).execute(
        run_id=RUN_ID
    )

    assert result.status == "EMPTY"
    assert result.samples == ()
    assert result.manifest["rejected_counts"][reason] == 1
    assert result.summary.invalid == 1


@pytest.mark.asyncio
async def test_held_or_rejected_prior_candidate_does_not_suppress_later_export(
    tmp_path,
):
    repository = FakeReviewRepository([_candidate(1)])
    use_case = RetrainingExportUseCase(repository, output_root=tmp_path)

    first = await use_case.execute(run_id=RUN_ID)
    assert [sample.traffic_log_id for sample in first.samples] == [1]

    repository.candidates = [_candidate(1), _candidate(2, label="Normal")]
    second = await use_case.execute(run_id="retrain-20260810T120002Z-000000000003")
    assert [sample.traffic_log_id for sample in second.samples] == [1, 2]


@pytest.mark.asyncio
async def test_export_quarantines_concentration_and_total_limit_violations(tmp_path):
    repository = FakeReviewRepository([_candidate(1), _candidate(2)])
    use_case = RetrainingExportUseCase(
        repository,
        output_root=tmp_path,
        max_total_additions=1,
        max_source_fraction=0.5,
        source_concentration_min_samples=2,
    )

    result = await use_case.execute(run_id=RUN_ID)

    assert result.status == "QUARANTINED_FOR_REVIEW"
    assert result.samples == ()
    assert result.manifest["rejected_counts"]["TOTAL_LIMIT_EXCEEDED"] == 1
    assert result.manifest["rejected_counts"]["SOURCE_CONCENTRATION_LIMIT"] == 1


@pytest.mark.asyncio
async def test_empty_eligible_data_is_explicit(tmp_path):
    repository = FakeReviewRepository(
        [_candidate(1, approval_state="excluded_from_training")]
    )

    result = await RetrainingExportUseCase(repository, output_root=tmp_path).execute(
        run_id=RUN_ID
    )

    assert result.status == "EMPTY"
    assert result.samples == ()
    assert result.manifest["row_count"] == 0
