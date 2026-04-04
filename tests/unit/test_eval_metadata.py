"""
Unit tests for eval_metadata loading in ModelService.

Tests cover:
- metadata present (valid JSON with all fields)
- metadata absent (no eval directory or files)
- malformed JSON (invalid JSON in eval file)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from web_app.services.model_service import ModelService


class TestEvalMetadata:
    """Test cases for eval metadata loading via instance method."""

    @pytest.fixture
    def temp_run_dir(self):
        """Create a temporary directory for mock run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_service(self, temp_run_dir):
        """Create a ModelService mock instance with _load_eval_metadata available."""
        service = ModelService.__new__(ModelService)
        service.settings = None
        service.device = "cpu"
        service.model = None
        service.tokenizer = None
        service.temperature = 0.5
        service.model_version = "test"
        service._mock_classifier = None
        service._total_processed = 0
        service._total_inference_latency_ms = 0.0
        service._confidence_low_threshold = 0.50
        service._confidence_high_threshold = 0.80
        service._eval_metadata = {}
        return service

    def test_metadata_present_full_eval_results(self, mock_service, temp_run_dir):
        """Test loading eval metadata when full eval results are present."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        eval_data = {
            "macro_f1": 0.9234,
            "ece": 0.0456,
            "per_class": {
                "SQL Injection": {
                    "f1": 0.95,
                    "precision": 0.93,
                    "recall": 0.97,
                    "support": 1500,
                },
                "Code Injection": {
                    "f1": 0.89,
                    "precision": 0.87,
                    "recall": 0.91,
                    "support": 800,
                },
                "Other Attacks": {
                    "f1": 0.78,
                    "precision": 0.75,
                    "recall": 0.81,
                    "support": 400,
                },
                "Normal": {
                    "f1": 0.98,
                    "precision": 0.99,
                    "recall": 0.97,
                    "support": 5000,
                },
            },
            "calibration_bins": [
                {"bin": 0, "avg_conf": 0.05, "avg_acc": 0.04, "gap": 0.01, "count": 50},
                {
                    "bin": 1,
                    "avg_conf": 0.15,
                    "avg_acc": 0.14,
                    "gap": 0.01,
                    "count": 100,
                },
                {
                    "bin": 2,
                    "avg_conf": 0.25,
                    "avg_acc": 0.24,
                    "gap": 0.01,
                    "count": 150,
                },
            ],
        }

        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text(json.dumps(eval_data))

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        assert metadata["macro_f1"] == 0.9234
        assert metadata["ece"] == 0.0456
        assert "per_class_f1" in metadata
        assert metadata["per_class_f1"]["SQL Injection"] == 0.95
        assert metadata["per_class_f1"]["Code Injection"] == 0.89
        assert metadata["per_class_f1"]["Other Attacks"] == 0.78
        assert metadata["per_class_f1"]["Normal"] == 0.98
        assert "calibration_bins" in metadata
        assert len(metadata["calibration_bins"]) == 3
        assert "prediction_distribution" in metadata
        assert metadata["prediction_distribution"]["SQL Injection"] == 1500

    def test_metadata_present_partial_eval_results(self, mock_service, temp_run_dir):
        """Test loading eval metadata with partial fields."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        eval_data = {
            "macro_f1": 0.89,
            "per_class": {
                "SQL Injection": {"f1": 0.92, "support": 100},
                "Normal": {"f1": 0.95, "support": 200},
            },
        }

        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text(json.dumps(eval_data))

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        assert metadata["macro_f1"] == 0.89
        assert "ece" not in metadata
        assert metadata["per_class_f1"]["SQL Injection"] == 0.92
        assert metadata["per_class_f1"]["Normal"] == 0.95

    def test_metadata_absent_no_eval_directory(self, mock_service, temp_run_dir):
        """Test that missing eval directory returns empty dict."""
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_metadata_absent_no_eval_file(self, mock_service, temp_run_dir):
        """Test that eval directory without results file returns empty dict."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_metadata_absent_wrong_filename(self, mock_service, temp_run_dir):
        """Test that eval file with wrong name returns empty dict."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        wrong_file = eval_dir / "eval_results_others.json"
        wrong_file.write_text(json.dumps({"macro_f1": 0.9}))
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_malformed_json_invalid_json(self, mock_service, temp_run_dir):
        """Test that malformed JSON returns empty dict."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text("{ invalid json content")
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_malformed_json_partial_corruption(self, mock_service, temp_run_dir):
        """Test that partially corrupted JSON returns empty results."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text('{"macro_f1": 0.9, "invalid": {broken}')
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_malformed_json_empty_file(self, mock_service, temp_run_dir):
        """Test that empty eval file returns empty dict."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text("")
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata == {}

    def test_malformed_json_null_value(self, mock_service, temp_run_dir):
        """Test that null values in JSON are handled without crashing."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text('{"macro_f1": null, "ece": 0.05}')
        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert "macro_f1" not in metadata
        assert metadata["ece"] == 0.05

    def test_malformed_json_wrong_types(self, mock_service, temp_run_dir):
        """Test that wrong numeric types are rejected clearly."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()
        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text('{"macro_f1": "not a number", "ece": "also not a number"}')
        with pytest.raises(ValueError):
            mock_service._load_eval_metadata(temp_run_dir)

    def test_calibration_bins_transformed_correctly(self, mock_service, temp_run_dir):
        """Test that calibration bins are transformed to correct schema."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        eval_data = {
            "calibration_bins": [
                {"bin": 0, "avg_conf": 0.1, "avg_acc": 0.15, "count": 50},
                {"bin": 1, "avg_conf": 0.3, "avg_acc": 0.28, "count": 100},
                {"bin": 2, "avg_conf": 0.5, "avg_acc": 0.52, "count": 150},
            ],
        }

        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text(json.dumps(eval_data))

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        bins = metadata["calibration_bins"]
        assert len(bins) == 3

        assert bins[0]["bin_idx"] == 0
        assert bins[0]["bin_center"] == 0.1
        assert bins[0]["accuracy"] == 0.15
        assert bins[0]["confidence"] == 0.1
        assert bins[0]["count"] == 50

        assert bins[1]["bin_idx"] == 1
        assert bins[2]["bin_center"] == 0.5

    def test_per_class_f1_extracted_correctly(self, mock_service, temp_run_dir):
        """Test that per_class_f1 is correctly extracted from per_class."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        eval_data = {
            "per_class": {
                "SQL Injection": {"f1": 0.97, "precision": 0.95, "recall": 0.99},
                "Code Injection": {"f1": 0.88, "precision": 0.86, "recall": 0.90},
                "Normal": {"f1": 0.99},
            },
        }

        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text(json.dumps(eval_data))

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        per_class_f1 = metadata["per_class_f1"]
        assert per_class_f1["SQL Injection"] == 0.97
        assert per_class_f1["Code Injection"] == 0.88
        assert per_class_f1["Normal"] == 0.99

    def test_prediction_distribution_extracted_correctly(
        self, mock_service, temp_run_dir
    ):
        """Test that prediction_distribution is extracted from support."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        eval_data = {
            "per_class": {
                "SQL Injection": {"support": 1500, "f1": 0.9},
                "Code Injection": {"support": 750, "f1": 0.8},
                "Other Attacks": {"support": 250, "f1": 0.7},
                "Normal": {"support": 4500, "f1": 0.95},
            },
        }

        eval_file = eval_dir / "eval_results_distilbert_calibrated.json"
        eval_file.write_text(json.dumps(eval_data))

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        dist = metadata["prediction_distribution"]
        assert dist["SQL Injection"] == 1500
        assert dist["Code Injection"] == 750
        assert dist["Other Attacks"] == 250
        assert dist["Normal"] == 4500

    def test_multiple_eval_dirs_picks_latest(self, mock_service, temp_run_dir):
        """Test that when multiple eval dirs exist, latest is chosen."""
        eval_dir = temp_run_dir / "eval"
        eval_dir.mkdir()

        old_dir = eval_dir / "20250101_000000"
        old_dir.mkdir()
        old_file = old_dir / "eval_results_distilbert_calibrated.json"
        old_file.write_text(json.dumps({"macro_f1": 0.80}))

        new_dir = eval_dir / "20260101_000000"
        new_dir.mkdir()
        new_file = new_dir / "eval_results_distilbert_calibrated.json"
        new_file.write_text(json.dumps({"macro_f1": 0.95}))

        metadata = mock_service._load_eval_metadata(temp_run_dir)
        assert metadata["macro_f1"] == 0.95

    def test_packaged_eval_report_is_used_when_eval_dir_missing(
        self, mock_service, temp_run_dir
    ):
        """Test that packaged eval_report.json populates ML health metadata."""
        eval_data = {
            "SQL Injection": {"f1-score": 0.99, "support": 8975},
            "Normal": {"f1-score": 0.98, "support": 3658},
            "macro avg": {"f1-score": 0.9885, "support": 19505},
            "accuracy": 0.9925,
        }

        eval_file = temp_run_dir / "eval_report.json"
        eval_file.write_text(json.dumps(eval_data), encoding="utf-8")

        metadata = mock_service._load_eval_metadata(temp_run_dir)

        assert metadata["macro_f1"] == pytest.approx(0.9885)
        assert metadata["per_class_f1"]["SQL Injection"] == pytest.approx(0.99)
        assert metadata["prediction_distribution"]["SQL Injection"] == 8975


class TestEvalMetadataProperty:
    """Test cases for the eval_metadata property on ModelService."""

    def test_eval_metadata_property_returns_copy(self):
        """Test that eval_metadata property returns a copy, not the original."""
        service = ModelService.create_mock()
        service._eval_metadata = {"macro_f1": 0.9}
        metadata = service.eval_metadata
        metadata["macro_f1"] = 0.99
        assert service.eval_metadata["macro_f1"] == 0.9

    def test_eval_metadata_property_mock_service(self):
        """Test eval_metadata property on mock service."""
        service = ModelService.create_mock()
        assert service.eval_metadata == {}
