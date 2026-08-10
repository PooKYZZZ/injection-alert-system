from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ml_model.retraining.dashboard_contracts import (
    ArtifactLayoutError,
    ContractValidationError,
    Decision,
    DecisionValue,
    EvidenceStatus,
    ExportedSample,
    MetricDefinition,
    MetricKind,
    RejectionReason,
    RunManifest,
    RunState,
    build_run_id,
    canonical_json,
    get_run_artifact_directory,
    is_valid_run_id,
)


def _metric(**overrides) -> MetricDefinition:
    payload = {
        "name": "macro_f1",
        "value": 0.9,
        "numerator": 9,
        "denominator": 10,
        "numerator_definition": "correct per-class F1 aggregate",
        "denominator_definition": "supported classes in the evaluation split",
        "ground_truth_source": "verified_label",
        "evaluation_split": "frozen_holdout",
        "support_count": 10,
        "evidence_status": EvidenceStatus.VERIFIED,
        "metric_kind": MetricKind.GROUND_TRUTH,
    }
    payload.update(overrides)
    return MetricDefinition(**payload)


def test_run_id_and_artifact_layout_are_stable_and_allowlisted(tmp_path):
    created_at = datetime(2026, 8, 10, 12, 30, 45, tzinfo=timezone.utc)
    run_id = build_run_id(created_at, entropy="contract-test")

    assert is_valid_run_id(run_id)
    assert run_id == build_run_id(created_at, entropy="contract-test")
    assert get_run_artifact_directory(tmp_path, run_id) == tmp_path / run_id

    with pytest.raises(ArtifactLayoutError):
        get_run_artifact_directory(tmp_path, "../../outside")


def test_metric_definition_rejects_passing_evidence_without_support():
    with pytest.raises(ContractValidationError, match="support"):
        _metric(value=0.0, denominator=None, support_count=0)


def test_run_manifest_and_exported_sample_have_deterministic_json():
    run_id = build_run_id(
        datetime(2026, 8, 10, 12, 30, 45, tzinfo=timezone.utc),
        entropy="manifest-test",
    )
    manifest = RunManifest(
        run_id=run_id,
        state=RunState.QUEUED,
        created_at="2026-08-10T12:30:45Z",
        trigger="manual",
        requested_by="reviewer-1",
        requested_timezone="Asia/Manila",
        dataset_version="approved-v1",
        dataset_digest="a" * 64,
        preprocessing_version="http-preprocessor-v2",
        active_model_version="active-v1",
        active_model_digest="b" * 64,
        pipeline_version="dashboard-retraining.v1",
    )
    sample = ExportedSample(
        sample_id="traffic-7-r2",
        traffic_log_id=7,
        review_revision=2,
        model_input_text="GET /health",
        model_input_hash="c" * 64,
        verified_label="Normal",
        predicted_label="SQL Injection",
        prediction_confidence=0.99,
        prediction_confidence_level="CRITICAL",
        model_version="active-v1",
        preprocessing_version="http-preprocessor-v2",
        reviewer_id="reviewer-1",
    )
    rejection = RejectionReason(code="duplicate", count=1)

    first = canonical_json(
        {"manifest": manifest, "sample": sample, "rejection": rejection}
    )
    second = canonical_json(
        {"rejection": rejection, "sample": sample, "manifest": manifest}
    )

    assert first == second
    assert json.loads(first)["manifest"]["state"] == "queued"
    assert json.loads(first)["sample"]["verified_label"] == "Normal"


def test_decision_payload_is_strict_and_bounded():
    run_id = build_run_id(
        datetime(2026, 8, 10, 12, 30, 45, tzinfo=timezone.utc),
        entropy="decision-test",
    )
    payload = {
        "decision": "hold",
        "run_id": run_id,
        "candidate_model_digest": "a" * 64,
        "dataset_digest": "b" * 64,
        "evaluation_digest": "c" * 64,
        "active_model_digest": "d" * 64,
        "reviewer_id": "reviewer-1",
        "reason": "Insufficient support for the attack classes.",
    }

    decision = Decision.from_payload(payload)
    assert decision.decision is DecisionValue.HOLD

    with pytest.raises(ContractValidationError, match="unknown fields"):
        Decision.from_payload({**payload, "artifact_root": "C:/unsafe"})
    with pytest.raises(ContractValidationError, match="decision"):
        Decision.from_payload({**payload, "decision": "promote"})
    with pytest.raises(ContractValidationError, match="reason"):
        Decision.from_payload({**payload, "decision": "reject", "reason": ""})
