import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.retraining.dashboard_contracts import ExportedSample
from ml_model.retraining.dashboard_dataset import build_dashboard_dataset_snapshot

RUN_ID = "retrain-20260810T120000Z-000000000001"


def _write_historical_dataset(root: Path) -> dict[str, bytes]:
    root.mkdir(parents=True)
    frames = {
        "train": pd.DataFrame(
            {
                "combined_payload": ["get /historical/train"],
                "final_label": ["Normal"],
                "sample_id": ["historical-train-1"],
                "source_type": ["fixture"],
            }
        ),
        "validation": pd.DataFrame(
            {
                "combined_payload": ["get /historical/validation"],
                "final_label": ["SQL Injection"],
                "sample_id": ["historical-validation-1"],
                "source_type": ["fixture"],
            }
        ),
        "test": pd.DataFrame(
            {
                "combined_payload": ["get /historical/test"],
                "final_label": ["Code Injection"],
                "sample_id": ["historical-test-1"],
                "source_type": ["fixture"],
            }
        ),
    }
    contents: dict[str, bytes] = {}
    for split, frame in frames.items():
        frame.to_parquet(root / f"{split}.parquet", index=False)
        contents[split] = (root / f"{split}.parquet").read_bytes()
    checksums = (
        "\n".join(
            f"{hashlib.sha256(contents[split]).hexdigest()}  {split}.parquet"
            for split in ("train", "validation", "test")
        )
        + "\n"
    )
    (root / "checksums.txt").write_text(checksums, encoding="utf-8")
    (root / "metadata_preprocessing.json").write_text(
        json.dumps(
            {
                "dataset_version": "v3_907k_cleaned",
                "preprocessing_version": MODEL_INPUT_VERSION,
                "text_column": "combined_payload",
                "model_input_hash_policy": "sha256(model_input_text)",
            }
        ),
        encoding="utf-8",
    )
    return contents


def _sample(sample_id: str, text: str, label: str = "Other Attacks") -> ExportedSample:
    return ExportedSample(
        sample_id=sample_id,
        traffic_log_id=int(sample_id.split("-")[-1]),
        review_revision=1,
        model_input_text=text,
        model_input_hash=hashlib.sha256(text.encode()).hexdigest(),
        verified_label=label,
        predicted_label=None,
        prediction_confidence=None,
        prediction_confidence_level=None,
        model_version="model-v1",
        preprocessing_version=MODEL_INPUT_VERSION,
        reviewer_id="analyst-1",
        reviewed_at=datetime(2026, 8, 10, tzinfo=timezone.utc).isoformat(),
        source_provenance="DIRECT_REMOTE_ADDR",
        source_verification_status="UNVERIFIED",
        ingest_event_hash="c" * 64,
    )


def test_snapshot_is_cumulative_and_preserves_frozen_holdouts(tmp_path):
    historical = tmp_path / "historical"
    original = _write_historical_dataset(historical)

    run_one = build_dashboard_dataset_snapshot(
        run_id=RUN_ID,
        exported_samples=[_sample("review-1", "get /approved/a")],
        historical_data_dir=historical,
        output_root=tmp_path / "runs",
        source_dataset_version="v3_907k_cleaned",
    )
    run_two = build_dashboard_dataset_snapshot(
        run_id="retrain-20260810T120001Z-000000000002",
        exported_samples=[
            _sample("review-1", "get /approved/a"),
            _sample(
                "review-2",
                "post /totally-different-endpoint-with-a-long-distinct-value",
                "SQL Injection",
            ),
        ],
        historical_data_dir=historical,
        output_root=tmp_path / "runs",
        source_dataset_version="v3_907k_cleaned",
    )

    first_train = pd.read_parquet(run_one.dataset_dir / "train.parquet")
    second_train = pd.read_parquet(run_two.dataset_dir / "train.parquet")
    assert len(first_train) == 2
    assert len(second_train) == 3
    assert set(second_train["combined_payload"]) >= {
        "get /approved/a",
        "post /totally-different-endpoint-with-a-long-distinct-value",
    }
    assert run_two.dataset_version.startswith("dashboard-")
    assert (run_two.dataset_dir / "dataset_manifest.json").is_file()
    assert (run_two.dataset_dir / "validation.parquet").read_bytes() == original[
        "validation"
    ]
    assert (run_two.dataset_dir / "test.parquet").read_bytes() == original["test"]
    assert (historical / "train.parquet").read_bytes() == original["train"]


def test_excluded_latest_is_not_exported_and_contamination_fails_closed(tmp_path):
    historical = tmp_path / "historical"
    _write_historical_dataset(historical)

    with pytest.raises(ValueError, match="contamination"):
        build_dashboard_dataset_snapshot(
            run_id=RUN_ID,
            exported_samples=[_sample("review-1", "get /historical/test")],
            historical_data_dir=historical,
            output_root=tmp_path / "runs",
            source_dataset_version="v3_907k_cleaned",
        )


def test_unknown_preprocessing_metadata_is_rejected(tmp_path):
    historical = tmp_path / "historical"
    _write_historical_dataset(historical)
    metadata_path = historical / "metadata_preprocessing.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["preprocessing_version"] = "unknown-real-artifact"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="preprocessing"):
        build_dashboard_dataset_snapshot(
            run_id=RUN_ID,
            exported_samples=[],
            historical_data_dir=historical,
            output_root=tmp_path / "runs",
            source_dataset_version="v3_907k_cleaned",
        )


def test_locked_golden_overlap_is_rejected(tmp_path):
    historical = tmp_path / "historical"
    _write_historical_dataset(historical)

    with pytest.raises(ValueError, match="golden"):
        build_dashboard_dataset_snapshot(
            run_id=RUN_ID,
            exported_samples=[_sample("review-1", "GET /records/search")],
            historical_data_dir=historical,
            output_root=tmp_path / "runs",
            source_dataset_version="v3_907k_cleaned",
        )


def test_snapshot_does_not_write_to_frozen_dataset(tmp_path):
    historical = tmp_path / "data" / "processed" / "v3_907k_cleaned"
    _write_historical_dataset(historical)
    before = sorted(path.relative_to(historical) for path in historical.rglob("*"))

    result = build_dashboard_dataset_snapshot(
        run_id=RUN_ID,
        exported_samples=[],
        historical_data_dir=historical,
        output_root=tmp_path / "runs",
        source_dataset_version="v3_907k_cleaned",
    )

    assert result.dataset_dir != historical
    assert (
        sorted(path.relative_to(historical) for path in historical.rglob("*")) == before
    )
