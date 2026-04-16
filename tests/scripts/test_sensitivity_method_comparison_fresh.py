from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sensitivity_method_comparison_fresh.py"
REAL_RUN_DIR = (
    REPO_ROOT
    / "ml_model"
    / "notebooks"
    / "training done"
    / "Final training"
    / "results"
    / "v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "sensitivity_method_comparison_fresh",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_latest_valid_run_dir_returns_valid_candidate(tmp_path):
    module = load_module()

    invalid_run = tmp_path / "invalid_run"
    invalid_run.mkdir(parents=True)

    valid_a = tmp_path / "valid_a"
    (valid_a / "evaluation").mkdir(parents=True)
    (valid_a / "model_benchmark_summary.csv").write_text("model_key\nminilm_l6\n", encoding="utf-8")
    (valid_a / "evaluation" / "aggregated_per_class_summary.csv").write_text(
        "model_key,label_name,recall_mean\nminilm_l6,normal,0.99\n",
        encoding="utf-8",
    )

    valid_b = tmp_path / "valid_b"
    (valid_b / "evaluation").mkdir(parents=True)
    (valid_b / "model_benchmark_summary.csv").write_text("model_key\ndistilbert\n", encoding="utf-8")
    (valid_b / "evaluation" / "aggregated_per_class_summary.csv").write_text(
        "model_key,label_name,recall_mean\ndistilbert,normal,0.99\n",
        encoding="utf-8",
    )

    os.utime(valid_a, (1_700_000_000, 1_700_000_000))
    os.utime(valid_b, (1_800_000_000, 1_800_000_000))

    selected = module.find_latest_valid_run_dir(tmp_path)
    assert selected == valid_b


def test_extracts_exact_five_metrics_from_real_run():
    module = load_module()

    data = module.build_core_metric_data(REAL_RUN_DIR)

    assert sorted(data["metric_names"]) == sorted(
        [
            "Attack-Class Recall",
            "Normal False Positive Rate",
            "Inference Time",
            "Model Size",
            "Training Runtime",
        ]
    )

    for model_key in data["model_keys"]:
        assert sorted(data["raw_metrics"][model_key].keys()) == sorted(data["metric_names"])


def test_metric_direction_mapping_is_correct():
    module = load_module()

    data = module.build_core_metric_data(REAL_RUN_DIR)

    assert data["metric_directions"] == {
        "Attack-Class Recall": True,
        "Normal False Positive Rate": False,
        "Inference Time": False,
        "Model Size": False,
        "Training Runtime": False,
    }


def test_option_1_reports_preferred_and_conditional_tiers(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    result = module.run_option_1_security_gate(
        core_data=core_data,
        output_dir=tmp_path / "option_1_security_gate",
        gate_policy=module.GatePolicy(),
    )
    method_summary = json.loads(
        (tmp_path / "option_1_security_gate" / "method_summary.json").read_text(encoding="utf-8")
    )

    assert "gate_policy" in method_summary
    assert "minimum_acceptable" in method_summary["gate_policy"]
    assert "preferred" in method_summary["gate_policy"]
    assert "operational_constraint" in method_summary["gate_policy"]

    assert "preferred_models" in method_summary
    assert "conditionally_eligible_models" in method_summary
    assert "ineligible_models" in method_summary
    assert "eligible_models" in method_summary
    assert all("tier" in row for row in method_summary["gate_results"])

    eligible_models = set(method_summary["eligible_models"])
    assert set(result["ranking"]).issubset(eligible_models)


def test_option_1_no_fallback_when_zero_models_pass(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    gate = module.GatePolicy(
        minimum_acceptable_min_attack_class_recall=0.999999,
        minimum_acceptable_max_normal_false_positive_rate=0.000001,
        preferred_min_attack_class_recall=0.999999,
        preferred_max_normal_false_positive_rate=0.000001,
        operational_max_inference_time_ms=50.0,
        zero_pass_behavior="no_ranking",
    )

    summary = module.run_option_1_security_gate(
        core_data=core_data,
        output_dir=tmp_path / "option_1_security_gate",
        gate_policy=gate,
    )
    method_summary = json.loads(
        (tmp_path / "option_1_security_gate" / "method_summary.json").read_text(encoding="utf-8")
    )

    assert summary["winner"] is None
    assert summary["ranking"] == []
    assert summary["ranking_performed"] is False
    assert "No eligible model under current gate" in summary["note"]
    assert method_summary["preferred_models"] == []
    assert method_summary["conditionally_eligible_models"] == []
    assert len(method_summary["ineligible_models"]) == len(core_data["model_keys"])


def test_option_1_default_policy_produces_eligible_models_on_real_benchmark(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    result = module.run_option_1_security_gate(
        core_data=core_data,
        output_dir=tmp_path / "option_1_security_gate",
        gate_policy=module.GatePolicy(),
    )
    method_summary = json.loads(
        (tmp_path / "option_1_security_gate" / "method_summary.json").read_text(encoding="utf-8")
    )

    assert method_summary["preferred_models"] or method_summary["conditionally_eligible_models"]
    assert result["ranking_performed"] is True
    assert result["winner"] in core_data["model_keys"]
    assert set(result["ranking"]).issubset(set(method_summary["eligible_models"]))


def test_option_1_latency_is_operational_not_core_security_gate(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    slow_model = core_data["model_keys"][0]
    core_data["raw_metrics"][slow_model]["Inference Time"] = 120.0
    core_data["normalized_metrics"] = module.normalize_metric_matrix(
        core_data["raw_metrics"],
        core_data["metric_directions"],
    )

    module.run_option_1_security_gate(
        core_data=core_data,
        output_dir=tmp_path / "option_1_security_gate",
        gate_policy=module.GatePolicy(),
    )
    method_summary = json.loads(
        (tmp_path / "option_1_security_gate" / "method_summary.json").read_text(encoding="utf-8")
    )

    slow_row = next(
        row for row in method_summary["gate_results"] if row["model_key"] == slow_model
    )
    assert slow_row["passed_minimum"] is True
    assert slow_row["tier"] in {"preferred", "conditionally_eligible"}
    assert slow_row["passed_operational_latency"] is False
    assert not any("Inference Time" in reason for reason in slow_row["failure_reasons"])
    assert slow_model in method_summary["eligible_models"]


def test_option_2_is_grouped_and_primary_only(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    summary = module.run_option_2_grouped_weighting(
        core_data=core_data,
        output_dir=tmp_path / "option_2_grouped_weighting",
    )

    assert summary["winner"] in core_data["model_keys"]
    assert len(summary["ranking"]) == len(core_data["model_keys"])
    assert "group_weights" in summary
    assert "group_definitions" in summary
    assert "supplementary" not in summary
    assert "unconstrained" not in summary


def test_option_3_is_flat_five_metric_output(tmp_path):
    module = load_module()

    core_data = module.build_core_metric_data(REAL_RUN_DIR)
    summary = module.run_option_3_direct_five_metric(
        core_data=core_data,
        output_dir=tmp_path / "option_3_direct_five_metric",
        seed=17,
        sample_count=256,
        display_sample_count=64,
    )

    assert summary["winner"] in core_data["model_keys"]
    assert sorted(summary["metrics_used"]) == sorted(core_data["metric_names"])
    assert len(summary["winner_frequency"]) == len(core_data["model_keys"])
    assert len(summary["average_rank"]) == len(core_data["model_keys"])


def test_parent_outputs_include_required_structure_and_figures(tmp_path):
    module = load_module()

    result = module.run_fresh_method_comparison(
        run_dir=REAL_RUN_DIR,
        output_root=tmp_path,
        seed=123,
        option_3_sample_count=256,
        option_3_display_sample_count=64,
    )

    parent_dir = Path(result["parent_dir"])
    assert parent_dir.exists()

    assert (parent_dir / "option_1_security_gate").exists()
    assert (parent_dir / "option_2_grouped_weighting").exists()
    assert (parent_dir / "option_3_direct_five_metric").exists()

    combined_summary = parent_dir / "combined_method_comparison_summary.json"
    comparison_table = parent_dir / "method_comparison_table.json"

    assert combined_summary.exists()
    assert comparison_table.exists()

    assert (parent_dir / "figure_1_ranked_lollipop.png").exists()
    assert (parent_dir / "figure_2_metric_heatmap.png").exists()
    assert (parent_dir / "figure_3_latency_vs_recall_pareto.png").exists()
    assert (parent_dir / "figure_4_error_bars_across_seeds.png").exists()
    assert (parent_dir / "figure_5_option_1_radar.png").exists()
    assert (parent_dir / "figure_6_option_2_radar.png").exists()
    assert (parent_dir / "figure_7_option_3_radar.png").exists()

    payload = json.loads(combined_summary.read_text(encoding="utf-8"))
    assert "parent_figures" in payload
    assert "figure_1_ranked_lollipop_png" in payload["parent_figures"]
    assert "figure_2_metric_heatmap_png" in payload["parent_figures"]
    assert "figure_3_latency_vs_recall_pareto_png" in payload["parent_figures"]
    assert "figure_4_error_bars_across_seeds_png" in payload["parent_figures"]
    assert "figure_5_option_1_radar_png" in payload["parent_figures"]
    assert "figure_6_option_2_radar_png" in payload["parent_figures"]
    assert "figure_7_option_3_radar_png" in payload["parent_figures"]

    assert "parent_figure_metadata" in payload
    assert payload["parent_figure_metadata"]["figure_5_option_1_radar"]["style_version"] == "legacy_engineering_v1"
    assert payload["parent_figure_metadata"]["figure_6_option_2_radar"]["axes"] == [
        "Security",
        "Efficiency",
        "Training Practicality",
    ]
    assert payload["parent_figure_metadata"]["figure_6_option_2_radar"]["source"] == "option_2_group_scores"
    assert payload["parent_figure_metadata"]["figure_6_option_2_radar"]["style_version"] == "legacy_engineering_v1"
    assert payload["parent_figure_metadata"]["figure_7_option_3_radar"]["style_version"] == "legacy_engineering_v1"
