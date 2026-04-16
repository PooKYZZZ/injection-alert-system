from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "sensitivity_analysis.py"
    )
    spec = importlib.util.spec_from_file_location("sensitivity_analysis", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalization_respects_metric_direction():
    module = load_module()

    designs = {
        "A": {"Gain": 0.9, "Cost": 100.0},
        "B": {"Gain": 0.8, "Cost": 150.0},
        "C": {"Gain": 0.7, "Cost": 200.0},
    }
    maximize_flags = {"Gain": True, "Cost": False}

    normalized = module.normalize_designs(designs, maximize_flags)

    assert normalized["A"]["Gain"] == 5.05
    assert normalized["C"]["Gain"] == 4.95
    assert normalized["A"]["Cost"] == 5.05
    assert normalized["C"]["Cost"] == 4.95


def test_sensitivity_analysis_uses_all_weight_permutations():
    module = load_module()

    normalized_designs = {
        "A": {"M1": 5.05, "M2": 4.95},
        "B": {"M1": 4.95, "M2": 5.05},
    }
    rating_scale = [6, 10]

    results, permutations, metrics = module.perform_sensitivity_analysis(
        normalized_designs,
        rating_scale,
        seed=42,
    )

    assert metrics == ["M1", "M2"]
    assert set(permutations) == {(6, 10), (10, 6)}
    assert len(results["A"]) == 2
    assert len(results["B"]) == 2
    assert results["A"] != results["B"]


def test_validate_inputs_rejects_mismatched_metric_sets():
    module = load_module()

    designs = {
        "A": {"M1": 0.9, "M2": 0.8},
        "B": {"M1": 0.7},
    }

    try:
        module.validate_inputs(designs, [6, 7], {"M1": True, "M2": True})
    except ValueError as exc:
        assert "same metrics" in str(exc)
    else:
        raise AssertionError("Expected validate_inputs to reject inconsistent metrics.")


def test_write_summary_json_persists_scores(tmp_path):
    module = load_module()
    output_path = tmp_path / "summary.json"

    module.write_summary_json(
        [("Model A", 5.01, 4.99, 5.03)],
        output_path,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == [
        {
            "design": "Model A",
            "mean_score": 5.01,
            "min_score": 4.99,
            "max_score": 5.03,
        }
    ]


def test_build_comparison_design_data_derives_security_scores():
    module = load_module()

    source_designs = {
        "A": {
            "Test Macro F1": 0.9884,
            "Attack Escape Rate": 0.00227,
            "Normal FP Rate": 0.00137,
            "Model Size MB": 262.18,
            "Total Runtime (sec)": 1520.38,
        },
        "B": {
            "Test Macro F1": 0.9892,
            "Attack Escape Rate": 0.00196,
            "Normal FP Rate": 0.00219,
            "Model Size MB": 253.91,
            "Total Runtime (sec)": 1326.31,
        },
    }

    comparison = module.build_comparison_design_data(source_designs)

    assert comparison["A"]["Attack Recall"] == 0.99773
    assert comparison["A"]["Normal Traffic Safety Score"] == 0.99863
    assert comparison["B"]["Attack Recall"] == 0.99804
    assert comparison["B"]["Normal Traffic Safety Score"] == 0.99781
    assert comparison["A"]["Compactness Score"] < comparison["B"]["Compactness Score"]
    assert (
        comparison["A"]["Training Runtime Score"]
        < comparison["B"]["Training Runtime Score"]
    )


def test_prepare_profile_plot_data_scales_metrics_to_ten_point_range():
    module = load_module()

    comparison_designs = {
        "A": {
            "Test Macro F1": 0.988,
            "Attack Recall": 0.997,
            "Normal Traffic Safety Score": 0.998,
            "Compactness Score": 0.2,
            "Training Runtime Score": 0.1,
        },
        "B": {
            "Test Macro F1": 0.989,
            "Attack Recall": 0.998,
            "Normal Traffic Safety Score": 0.999,
            "Compactness Score": 0.3,
            "Training Runtime Score": 0.2,
        },
    }

    scaled = module.prepare_profile_plot_data(comparison_designs)

    assert scaled["A"]["Test Macro F1"] == 0.988
    assert scaled["B"]["Test Macro F1"] == 0.989
    assert scaled["A"]["Attack Recall"] == 0.997
    assert scaled["B"]["Attack Recall"] == 0.998
    assert scaled["A"]["Training Runtime Score"] == 0.1
    assert scaled["B"]["Training Runtime Score"] == 0.2


def test_create_run_output_dir_creates_unique_named_folder(tmp_path):
    module = load_module()

    output_dir = module.create_run_output_dir(tmp_path, "comparison_radar")

    assert output_dir.exists()
    assert output_dir.parent == tmp_path
    assert output_dir.name.startswith("comparison_radar_")


def test_split_profile_metrics_separates_quality_and_operational_metrics():
    module = load_module()

    profile_data = {
        "A": {
            "Test Macro F1": 0.98,
            "Attack Recall": 0.97,
            "Normal Traffic Safety Score": 0.99,
            "Compactness Score": 0.1,
            "Training Runtime Score": 0.2,
        }
    }

    quality, operational = module.split_profile_metrics(profile_data)

    assert list(quality["A"].keys()) == [
        "Test Macro F1",
        "Attack Recall",
        "Normal Traffic Safety Score",
    ]
    assert list(operational["A"].keys()) == ["Compactness Score", "Training Runtime Score"]
