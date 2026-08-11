import json
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.retraining.dashboard_export import (
    ExportLimits,
    export_dashboard_reviews,
)
from web_app.domain.retraining import RetrainingReviewCandidate

RUN_ID = "retrain-20260810T120000Z-000000000001"


def _candidate(
    traffic_log_id: int, *, text: str, label: str = "Normal"
) -> RetrainingReviewCandidate:
    return RetrainingReviewCandidate(
        review_id=traffic_log_id,
        traffic_log_id=traffic_log_id,
        revision=1,
        predicted_label=None,
        verified_label=label,
        approval_state="approved_for_training",
        reviewer_id="analyst-1",
        reviewer_role="ANALYST",
        reviewed_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        model_version="model-v1",
        prediction_confidence=None,
        prediction_confidence_level=None,
        model_input_hash=sha256(text.encode()).hexdigest(),
        model_input_text=text,
        preprocessing_version=MODEL_INPUT_VERSION,
        ingest_event_hash="b" * 64,
        source_verification_status="VERIFIED",
        source_provenance="CLOUDFLARE_CONNECTING_IP",
    )


def test_export_manifest_is_deterministic_and_raw_text_is_local_only(tmp_path):
    result = export_dashboard_reviews(
        [_candidate(2, text="GET /b"), _candidate(1, text="GET /a")],
        run_id=RUN_ID,
        output_root=tmp_path,
        source_dataset_version="v3_907k_cleaned",
        created_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
    )

    assert result.status == "READY"
    assert [sample.traffic_log_id for sample in result.samples] == [1, 2]
    assert result.manifest["source_review_revisions"] == ["1:1", "2:1"]
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    assert "GET /a" not in manifest_text
    assert "GET /b" not in manifest_text
    rows = [
        json.loads(line)
        for line in result.export_path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["model_input_text"] == "GET /a"
    assert rows[0]["source_provenance"] == "CLOUDFLARE_CONNECTING_IP"


def test_exact_and_normalized_duplicates_are_rejected(tmp_path):
    candidates = [
        _candidate(1, text="GET /search?b=2&a=1"),
        _candidate(2, text="get /search?a=1&b=2"),
    ]

    result = export_dashboard_reviews(
        candidates,
        run_id=RUN_ID,
        output_root=tmp_path,
        source_dataset_version="v3_907k_cleaned",
    )

    assert result.status == "READY"
    assert [sample.traffic_log_id for sample in result.samples] == [1]
    assert result.manifest["rejected_counts"]["DUPLICATE_MODEL_INPUT"] == 1
    assert result.summary.duplicate == 1


def test_export_directory_is_reserved_and_never_overwritten(tmp_path):
    export_dashboard_reviews(
        [_candidate(1, text="GET /a")],
        run_id=RUN_ID,
        output_root=tmp_path,
        source_dataset_version="v3_907k_cleaned",
    )

    with pytest.raises(FileExistsError):
        export_dashboard_reviews(
            [_candidate(1, text="GET /changed")],
            run_id=RUN_ID,
            output_root=tmp_path,
            source_dataset_version="v3_907k_cleaned",
        )

    assert "GET /a" in (
        tmp_path / RUN_ID / "export" / "approved_samples.jsonl"
    ).read_text(encoding="utf-8")


def test_limits_record_observed_values_without_truncating(tmp_path):
    result = export_dashboard_reviews(
        [_candidate(1, text="GET /a"), _candidate(2, text="GET /b")],
        run_id=RUN_ID,
        output_root=tmp_path,
        source_dataset_version="v3_907k_cleaned",
        limits=ExportLimits(max_total_additions=1),
    )

    assert result.status == "QUARANTINED_FOR_REVIEW"
    assert result.samples == ()
    assert result.manifest["limits"]["max_total_additions"] == 1
    assert result.manifest["observed"]["total_additions"] == 2


@pytest.mark.parametrize("label", ["Not a class", "", None])
def test_unknown_verified_labels_are_explicitly_rejected(tmp_path, label):
    candidate = _candidate(1, text="GET /a")
    candidate = RetrainingReviewCandidate(
        **{**candidate.__dict__, "verified_label": label}
    )
    result = export_dashboard_reviews(
        [candidate],
        run_id=RUN_ID,
        output_root=tmp_path,
        source_dataset_version="v3_907k_cleaned",
    )
    assert result.status == "EMPTY"
    assert result.manifest["rejected_counts"]["NON_CANONICAL_LABEL"] == 1
