from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = (
    REPO_ROOT
    / "ml_model"
    / "notebooks"
    / "training done"
    / "Final training"
    / "results"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "sensitivity_analysis_runs"

DEFAULT_BENCHMARK_SUMMARY_NAME = "model_benchmark_summary.csv"
DEFAULT_EVALUATION_SUMMARY_RELATIVE_PATH = Path("evaluation") / "final_model_comparison.csv"
DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH = Path("evaluation") / "aggregated_per_class_summary.csv"
DEFAULT_THRESHOLD_SUMMARY_RELATIVE_PATH = Path("evaluation") / "threshold_analysis_summary.csv"
DEFAULT_SEED_METRICS_RELATIVE_PATH = Path("evaluation") / "roc_pr_per_class_seed_metrics.csv"

OPTION_1_SUBDIR = "option_1_security_gate"
OPTION_2_SUBDIR = "option_2_grouped_weighting"
OPTION_3_SUBDIR = "option_3_direct_five_metric"

OPTION_1_NAME = "Security gate + post-screen ranking"
OPTION_2_NAME = "Grouped / hierarchical weighting"
OPTION_3_NAME = "Direct five-metric no-grouping sensitivity"

METRIC_NAMES = [
    "Attack-Class Recall",
    "Normal False Positive Rate",
    "Inference Time",
    "Model Size",
    "Training Runtime",
]

METRIC_DIRECTIONS = {
    "Attack-Class Recall": True,
    "Normal False Positive Rate": False,
    "Inference Time": False,
    "Model Size": False,
    "Training Runtime": False,
}

DEFAULT_MODEL_ORDER = (
    "tinybert_bigru_attn",
    "distilbert",
    "minilm_l6",
)

DEFAULT_MODEL_LABELS = {
    "tinybert_bigru_attn": "Model A: TinyBERT BiGRU Attention",
    "distilbert": "Model B: DistilBERT",
    "minilm_l6": "Model C: MiniLM-L6",
}

OPTION_1_POST_SCREEN_WEIGHTS = {
    "Attack-Class Recall": 0.40,
    "Normal False Positive Rate": 0.35,
    "Inference Time": 0.15,
    "Model Size": 0.05,
    "Training Runtime": 0.05,
}

OPTION_1_MINIMUM_ACCEPTABLE = {
    "min_attack_class_recall": 0.990,
    "max_normal_false_positive_rate": 0.010,
}

OPTION_1_PREFERRED = {
    "min_attack_class_recall": 0.994,
    "max_normal_false_positive_rate": 0.005,
}

OPTION_1_OPERATIONAL_CONSTRAINT = {
    "max_inference_time_ms": 50.0,
}

OPTION_2_GROUP_DEFINITIONS = {
    "Security": ["Attack-Class Recall", "Normal False Positive Rate"],
    "Efficiency": ["Inference Time", "Model Size"],
    "Training Practicality": ["Training Runtime"],
}

OPTION_2_GROUP_WEIGHTS = {
    "Security": 0.60,
    "Efficiency": 0.25,
    "Training Practicality": 0.15,
}

OPTION_2_WITHIN_GROUP_WEIGHTS = {
    "Security": {
        "Attack-Class Recall": 0.50,
        "Normal False Positive Rate": 0.50,
    },
    "Efficiency": {
        "Inference Time": 0.50,
        "Model Size": 0.50,
    },
    "Training Practicality": {
        "Training Runtime": 1.00,
    },
}

DEFAULT_RANDOM_SEED = 135
DEFAULT_OPTION_3_SAMPLE_COUNT = 4000
DEFAULT_OPTION_3_DISPLAY_SAMPLE_COUNT = 120

FIGURE_1_NAME = "figure_1_ranked_lollipop.png"
FIGURE_2_NAME = "figure_2_metric_heatmap.png"
FIGURE_3_NAME = "figure_3_latency_vs_recall_pareto.png"
FIGURE_4_NAME = "figure_4_error_bars_across_seeds.png"
FIGURE_5_NAME = "figure_5_option_1_radar.png"
FIGURE_6_NAME = "figure_6_option_2_radar.png"
FIGURE_7_NAME = "figure_7_option_3_radar.png"
RADAR_STYLE_VERSION = "legacy_engineering_v1"

FIGURE_4_METRICS = [
    "Attack-Class Recall",
    "Normal False Positive Rate",
    "Inference Time",
]


class GatePolicy:
    def __init__(
        self,
        minimum_acceptable_min_attack_class_recall: float = OPTION_1_MINIMUM_ACCEPTABLE["min_attack_class_recall"],
        minimum_acceptable_max_normal_false_positive_rate: float = OPTION_1_MINIMUM_ACCEPTABLE["max_normal_false_positive_rate"],
        preferred_min_attack_class_recall: float = OPTION_1_PREFERRED["min_attack_class_recall"],
        preferred_max_normal_false_positive_rate: float = OPTION_1_PREFERRED["max_normal_false_positive_rate"],
        operational_max_inference_time_ms: float | None = OPTION_1_OPERATIONAL_CONSTRAINT["max_inference_time_ms"],
        zero_pass_behavior: str = "no_ranking",
    ) -> None:
        self.minimum_acceptable_min_attack_class_recall = minimum_acceptable_min_attack_class_recall
        self.minimum_acceptable_max_normal_false_positive_rate = (
            minimum_acceptable_max_normal_false_positive_rate
        )
        self.preferred_min_attack_class_recall = preferred_min_attack_class_recall
        self.preferred_max_normal_false_positive_rate = preferred_max_normal_false_positive_rate
        self.operational_max_inference_time_ms = operational_max_inference_time_ms
        self.zero_pass_behavior = zero_pass_behavior


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def rows_by_model(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        model_key = row.get("model_key")
        if model_key:
            output[model_key] = row
    return output


def infer_model_order(model_keys: list[str]) -> list[str]:
    ordered = [model_key for model_key in DEFAULT_MODEL_ORDER if model_key in model_keys]
    remainder = sorted(model_key for model_key in model_keys if model_key not in ordered)
    return ordered + remainder


def parse_required_float(row: dict[str, str], field_name: str, *, source_path: Path) -> float:
    raw = row.get(field_name)
    if raw in (None, ""):
        raise ValueError(f"Missing required field '{field_name}' in {source_path}")
    return float(raw)


def parse_preferred_float(
    primary_row: dict[str, str] | None,
    secondary_row: dict[str, str] | None,
    field_name: str,
    *,
    primary_path: Path | None,
    secondary_path: Path | None,
) -> float:
    for row in (primary_row, secondary_row):
        if row is None:
            continue
        raw = row.get(field_name)
        if raw not in (None, ""):
            return float(raw)

    searched = [str(path) for path in (primary_path, secondary_path) if path is not None]
    raise ValueError(
        f"Missing required field '{field_name}' in source files: {', '.join(searched)}"
    )


def field_available_for_all_models(
    model_keys: list[str],
    evaluation_rows: dict[str, dict[str, str]],
    benchmark_rows: dict[str, dict[str, str]],
    field_name: str,
) -> bool:
    for model_key in model_keys:
        eval_row = evaluation_rows.get(model_key)
        bench_row = benchmark_rows.get(model_key)
        found = False
        for row in (eval_row, bench_row):
            if row is not None and row.get(field_name) not in (None, ""):
                found = True
                break
        if not found:
            return False
    return True


def extract_metric_values(
    model_keys: list[str],
    evaluation_rows: dict[str, dict[str, str]],
    benchmark_rows: dict[str, dict[str, str]],
    field_name: str,
    *,
    evaluation_path: Path | None,
    benchmark_path: Path,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for model_key in model_keys:
        values[model_key] = parse_preferred_float(
            evaluation_rows.get(model_key),
            benchmark_rows.get(model_key),
            field_name,
            primary_path=evaluation_path,
            secondary_path=benchmark_path,
        )
    return values


def compute_attack_class_recall(
    per_class_path: Path,
    model_keys: list[str],
) -> dict[str, float]:
    rows = [
        row
        for row in load_csv_rows(per_class_path)
        if row.get("model_key") in model_keys
    ]
    if not rows:
        raise ValueError(f"No per-class rows found for models in {per_class_path}")

    by_model: dict[str, list[float]] = {model_key: [] for model_key in model_keys}
    for row in rows:
        label_name = (row.get("label_name") or "").strip().lower()
        if label_name == "normal":
            continue

        recall_raw = row.get("recall_mean")
        if recall_raw in (None, ""):
            raise ValueError(
                f"Missing recall_mean for non-Normal label in {per_class_path}"
            )
        by_model[row["model_key"]].append(float(recall_raw))

    if any(len(values) == 0 for values in by_model.values()):
        raise ValueError(
            "Attack-Class Recall could not be computed because one or more models "
            "have no non-Normal class rows."
        )

    return {model_key: float(mean(values)) for model_key, values in by_model.items()}


def normalize_metric_matrix(
    raw_metrics: dict[str, dict[str, float]],
    metric_directions: dict[str, bool],
) -> dict[str, dict[str, float]]:
    if not raw_metrics:
        raise ValueError("Cannot normalize empty metric matrix.")

    model_keys = list(raw_metrics.keys())
    expected_metrics = set(raw_metrics[model_keys[0]].keys())
    if expected_metrics != set(metric_directions.keys()):
        raise ValueError("Raw metric names and metric directions do not align.")

    for model_key in model_keys[1:]:
        if set(raw_metrics[model_key].keys()) != expected_metrics:
            raise ValueError("All models must share the same metric keys.")

    normalized: dict[str, dict[str, float]] = {
        model_key: {} for model_key in model_keys
    }

    for metric_name, maximize in metric_directions.items():
        values = {model_key: raw_metrics[model_key][metric_name] for model_key in model_keys}
        min_value = min(values.values())
        max_value = max(values.values())

        if max_value == min_value:
            for model_key in model_keys:
                normalized[model_key][metric_name] = 1.0
            continue

        for model_key, value in values.items():
            if maximize:
                score = (value - min_value) / (max_value - min_value)
            else:
                score = (max_value - value) / (max_value - min_value)
            normalized[model_key][metric_name] = float(score)

    return normalized


def find_latest_valid_run_dir(results_root: Path) -> Path:
    if not results_root.exists():
        raise FileNotFoundError(f"Results root does not exist: {results_root}")

    candidates: list[Path] = []
    for candidate in results_root.iterdir():
        if not candidate.is_dir():
            continue
        benchmark_path = candidate / DEFAULT_BENCHMARK_SUMMARY_NAME
        per_class_path = candidate / DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH
        if benchmark_path.exists() and per_class_path.exists():
            candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(
            f"No valid benchmark result runs found under: {results_root}"
        )

    confirmatory = [candidate for candidate in candidates if "confirmatory" in candidate.name.lower()]
    selection_pool = confirmatory if confirmatory else candidates
    return max(selection_pool, key=lambda candidate: candidate.stat().st_mtime)


def build_core_metric_data(run_dir: Path) -> dict[str, object]:
    benchmark_path = run_dir / DEFAULT_BENCHMARK_SUMMARY_NAME
    evaluation_path = run_dir / DEFAULT_EVALUATION_SUMMARY_RELATIVE_PATH
    per_class_path = run_dir / DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH
    threshold_path = run_dir / DEFAULT_THRESHOLD_SUMMARY_RELATIVE_PATH
    seed_metrics_path = run_dir / DEFAULT_SEED_METRICS_RELATIVE_PATH

    if not benchmark_path.exists():
        raise FileNotFoundError(f"Missing benchmark summary CSV: {benchmark_path}")
    if not per_class_path.exists():
        raise FileNotFoundError(f"Missing per-class summary CSV: {per_class_path}")

    benchmark_rows = rows_by_model(load_csv_rows(benchmark_path))
    evaluation_rows = (
        rows_by_model(load_csv_rows(evaluation_path)) if evaluation_path.exists() else {}
    )

    model_keys = infer_model_order(list(benchmark_rows.keys()))
    if not model_keys:
        raise ValueError(f"No model rows found in benchmark summary: {benchmark_path}")

    attack_class_recall = compute_attack_class_recall(per_class_path, model_keys)

    normal_false_positive_rate = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "normal_false_positive_rate_mean",
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )

    if field_available_for_all_models(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_p95_ms_mean",
    ):
        inference_time_field = "inference_latency_p95_ms_mean"
    elif field_available_for_all_models(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_p50_ms_mean",
    ):
        inference_time_field = "inference_latency_p50_ms_mean"
    elif field_available_for_all_models(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_mean_ms_mean",
    ):
        inference_time_field = "inference_latency_mean_ms_mean"
    else:
        raise ValueError(
            "Missing inference latency fields: expected p95, p50, or mean latency." 
        )

    inference_time = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        inference_time_field,
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )

    model_size: dict[str, float] = {}
    for model_key in model_keys:
        model_size[model_key] = parse_required_float(
            benchmark_rows[model_key],
            "model_size_mb_mean",
            source_path=benchmark_path,
        )

    training_runtime = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "training_workflow_runtime_sec_mean",
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )

    raw_metrics: dict[str, dict[str, float]] = {model_key: {} for model_key in model_keys}
    for model_key in model_keys:
        raw_metrics[model_key]["Attack-Class Recall"] = attack_class_recall[model_key]
        raw_metrics[model_key]["Normal False Positive Rate"] = normal_false_positive_rate[model_key]
        raw_metrics[model_key]["Inference Time"] = inference_time[model_key]
        raw_metrics[model_key]["Model Size"] = model_size[model_key]
        raw_metrics[model_key]["Training Runtime"] = training_runtime[model_key]

    normalized_metrics = normalize_metric_matrix(raw_metrics, METRIC_DIRECTIONS)

    inference_std_field = inference_time_field.replace("_mean", "_std")
    seed_error_metrics: dict[str, dict[str, dict[str, float]]] = {
        metric_name: {} for metric_name in FIGURE_4_METRICS
    }

    for model_key in model_keys:
        benchmark_row = benchmark_rows[model_key]
        evaluation_row = evaluation_rows.get(model_key)

        try:
            attack_escape_mean = parse_required_float(
                benchmark_row,
                "attack_escape_rate_mean",
                source_path=benchmark_path,
            )
            attack_escape_std = parse_required_float(
                benchmark_row,
                "attack_escape_rate_std",
                source_path=benchmark_path,
            )
            attack_recall_mean = 1.0 - attack_escape_mean
            attack_recall_std = attack_escape_std
        except ValueError:
            attack_recall_mean = raw_metrics[model_key]["Attack-Class Recall"]
            attack_recall_std = 0.0

        normal_fpr_std = 0.0
        if evaluation_row is not None and evaluation_row.get("normal_false_positive_rate_std") not in (None, ""):
            normal_fpr_std = float(evaluation_row["normal_false_positive_rate_std"])
        elif benchmark_row.get("normal_false_positive_rate_std") not in (None, ""):
            normal_fpr_std = float(benchmark_row["normal_false_positive_rate_std"])

        inference_std = 0.0
        if evaluation_row is not None and evaluation_row.get(inference_std_field) not in (None, ""):
            inference_std = float(evaluation_row[inference_std_field])
        elif benchmark_row.get(inference_std_field) not in (None, ""):
            inference_std = float(benchmark_row[inference_std_field])

        seed_error_metrics["Attack-Class Recall"][model_key] = {
            "mean": float(attack_recall_mean),
            "std": float(max(attack_recall_std, 0.0)),
        }
        seed_error_metrics["Normal False Positive Rate"][model_key] = {
            "mean": raw_metrics[model_key]["Normal False Positive Rate"],
            "std": float(max(normal_fpr_std, 0.0)),
        }
        seed_error_metrics["Inference Time"][model_key] = {
            "mean": raw_metrics[model_key]["Inference Time"],
            "std": float(max(inference_std, 0.0)),
        }

    metric_sources = {
        "Attack-Class Recall": (
            f"{DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH}: mean recall over non-Normal labels"
        ),
        "Normal False Positive Rate": "normal_false_positive_rate_mean",
        "Inference Time": inference_time_field,
        "Model Size": "model_size_mb_mean",
        "Training Runtime": "training_workflow_runtime_sec_mean",
    }

    return {
        "run_dir": run_dir,
        "model_keys": model_keys,
        "model_labels": {
            model_key: DEFAULT_MODEL_LABELS.get(model_key, model_key)
            for model_key in model_keys
        },
        "metric_names": list(METRIC_NAMES),
        "metric_directions": dict(METRIC_DIRECTIONS),
        "metric_sources": metric_sources,
        "raw_metrics": raw_metrics,
        "normalized_metrics": normalized_metrics,
        "seed_error_metrics": seed_error_metrics,
        "source_paths": {
            "benchmark_summary_csv": benchmark_path,
            "evaluation_summary_csv": evaluation_path if evaluation_path.exists() else None,
            "per_class_summary_csv": per_class_path,
            "threshold_analysis_csv": threshold_path if threshold_path.exists() else None,
            "seed_metrics_csv": seed_metrics_path if seed_metrics_path.exists() else None,
        },
    }


def evaluate_gate(
    core_data: dict[str, object],
    gate_policy: GatePolicy,
) -> dict[str, object]:
    raw_metrics = core_data["raw_metrics"]
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]

    gate_results: list[dict[str, object]] = []
    preferred_models: list[str] = []
    conditionally_eligible_models: list[str] = []
    ineligible_models: list[str] = []

    for model_key in model_keys:
        metrics = raw_metrics[model_key]
        attack_recall = float(metrics["Attack-Class Recall"])
        normal_fpr = float(metrics["Normal False Positive Rate"])
        inference_time = float(metrics["Inference Time"])

        passed_minimum_recall = (
            attack_recall >= gate_policy.minimum_acceptable_min_attack_class_recall
        )
        passed_minimum_fpr = (
            normal_fpr <= gate_policy.minimum_acceptable_max_normal_false_positive_rate
        )
        passed_minimum = passed_minimum_recall and passed_minimum_fpr

        passed_preferred_recall = (
            attack_recall >= gate_policy.preferred_min_attack_class_recall
        )
        passed_preferred_fpr = (
            normal_fpr <= gate_policy.preferred_max_normal_false_positive_rate
        )
        passed_preferred = passed_preferred_recall and passed_preferred_fpr

        if gate_policy.operational_max_inference_time_ms is None:
            passed_operational_latency = True
        else:
            passed_operational_latency = (
                inference_time <= gate_policy.operational_max_inference_time_ms
            )

        failure_reasons: list[str] = []
        if not passed_minimum_recall:
            failure_reasons.append(
                "Attack-Class Recall below minimum acceptable threshold"
            )
        if not passed_minimum_fpr:
            failure_reasons.append(
                "Normal False Positive Rate above minimum acceptable threshold"
            )

        preferred_gap_reasons: list[str] = []
        if passed_minimum and not passed_preferred_recall:
            preferred_gap_reasons.append(
                "Attack-Class Recall below preferred threshold"
            )
        if passed_minimum and not passed_preferred_fpr:
            preferred_gap_reasons.append(
                "Normal False Positive Rate above preferred threshold"
            )

        operational_notes: list[str] = []
        if not passed_operational_latency:
            operational_notes.append(
                "Inference latency exceeds operational constraint"
            )

        if not passed_minimum:
            tier = "ineligible"
            ineligible_models.append(model_key)
        elif passed_preferred:
            tier = "preferred"
            preferred_models.append(model_key)
        else:
            tier = "conditionally_eligible"
            conditionally_eligible_models.append(model_key)

        gate_results.append(
            {
                "model_key": model_key,
                "label": model_labels.get(model_key, model_key),
                "attack_class_recall": attack_recall,
                "normal_false_positive_rate": normal_fpr,
                "inference_time": inference_time,
                "tier": tier,
                "passed_minimum": passed_minimum,
                "passed_preferred": passed_preferred,
                "passed_operational_latency": passed_operational_latency,
                "failure_reasons": failure_reasons,
                "preferred_gap_reasons": preferred_gap_reasons,
                "operational_notes": operational_notes,
            }
        )

    eligible_models = preferred_models + conditionally_eligible_models

    return {
        "preferred_models": preferred_models,
        "conditionally_eligible_models": conditionally_eligible_models,
        "eligible_models": eligible_models,
        "ineligible_models": ineligible_models,
        "gate_results": gate_results,
    }


def compute_weighted_scores(
    model_keys: list[str],
    normalized_metrics: dict[str, dict[str, float]],
    weights: dict[str, float],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for model_key in model_keys:
        score = 0.0
        for metric_name, weight in weights.items():
            score += float(normalized_metrics[model_key][metric_name]) * float(weight)
        scores[model_key] = float(score)
    return scores


def run_option_1_security_gate(
    *,
    core_data: dict[str, object],
    output_dir: Path,
    gate_policy: GatePolicy,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    model_labels = core_data["model_labels"]
    normalized_metrics = core_data["normalized_metrics"]

    gate_info = evaluate_gate(core_data, gate_policy)
    eligible_models = gate_info["eligible_models"]
    tier_by_model = {
        row["model_key"]: row["tier"] for row in gate_info["gate_results"]
    }

    ranking_performed = len(eligible_models) > 0
    if ranking_performed:
        ranking_pool = list(eligible_models)
        score_by_model = compute_weighted_scores(
            ranking_pool,
            normalized_metrics,
            OPTION_1_POST_SCREEN_WEIGHTS,
        )
        ranked_models = sorted(
            ranking_pool,
            key=lambda model_key: (-score_by_model[model_key], model_key),
        )
        winner = ranked_models[0]
        note = "Ranking performed on gate-eligible models only."
    else:
        ranking_pool = []
        ranked_models = []
        winner = None
        score_by_model = {}
        note = "No eligible model under current gate"

    ranking = []
    for rank, model_key in enumerate(ranked_models, start=1):
        ranking.append(
            {
                "rank": rank,
                "model_key": model_key,
                "label": model_labels.get(model_key, model_key),
                "tier": tier_by_model.get(model_key),
                "post_screen_score": float(score_by_model[model_key]),
            }
        )

    method_summary = {
        "timestamp": now_utc_iso(),
        "method": {
            "id": OPTION_1_SUBDIR,
            "name": OPTION_1_NAME,
            "mode": "gate_first_non_compensatory_two_tier",
        },
        "gate_policy": {
            "minimum_acceptable": {
                "min_attack_class_recall": gate_policy.minimum_acceptable_min_attack_class_recall,
                "max_normal_false_positive_rate": gate_policy.minimum_acceptable_max_normal_false_positive_rate,
            },
            "preferred": {
                "min_attack_class_recall": gate_policy.preferred_min_attack_class_recall,
                "max_normal_false_positive_rate": gate_policy.preferred_max_normal_false_positive_rate,
            },
            "operational_constraint": {
                "max_inference_time_ms": gate_policy.operational_max_inference_time_ms,
            },
            "zero_pass_behavior": gate_policy.zero_pass_behavior,
        },
        "gate_results": gate_info["gate_results"],
        "preferred_models": gate_info["preferred_models"],
        "conditionally_eligible_models": gate_info["conditionally_eligible_models"],
        "eligible_models": gate_info["eligible_models"],
        "ineligible_models": gate_info["ineligible_models"],
        "ranking_pool": ranking_pool,
        "ranking_performed": ranking_performed,
        "note": note,
        "winner": winner,
        "ranking": ranking,
        "post_screen_weights": dict(OPTION_1_POST_SCREEN_WEIGHTS),
        "artifacts": {
            "method_summary_json": str(output_dir / "method_summary.json"),
            "metric_snapshot_json": str(output_dir / "option_1_metric_snapshot.json"),
        },
    }

    metric_snapshot = {
        "metric_sources": core_data["metric_sources"],
        "raw_metrics": core_data["raw_metrics"],
        "normalized_metrics": core_data["normalized_metrics"],
    }

    write_json(output_dir / "option_1_metric_snapshot.json", metric_snapshot)
    write_json(output_dir / "method_summary.json", method_summary)

    return {
        "method_id": OPTION_1_SUBDIR,
        "method_name": OPTION_1_NAME,
        "winner": winner,
        "ranking": [item["model_key"] for item in ranking],
        "preferred_models": gate_info["preferred_models"],
        "conditionally_eligible_models": gate_info["conditionally_eligible_models"],
        "eligible_models": gate_info["eligible_models"],
        "ineligible_models": gate_info["ineligible_models"],
        "ranking_performed": ranking_performed,
        "note": note,
        "subfolder": str(output_dir),
        "method_summary_json": str(output_dir / "method_summary.json"),
    }


def run_option_2_grouped_weighting(
    *,
    core_data: dict[str, object],
    output_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    normalized_metrics = core_data["normalized_metrics"]

    group_scores: dict[str, dict[str, float]] = {model_key: {} for model_key in model_keys}
    total_scores: dict[str, float] = {model_key: 0.0 for model_key in model_keys}

    for group_name, metric_names in OPTION_2_GROUP_DEFINITIONS.items():
        within_group_weights = OPTION_2_WITHIN_GROUP_WEIGHTS[group_name]
        group_weight = OPTION_2_GROUP_WEIGHTS[group_name]

        for model_key in model_keys:
            group_score = 0.0
            for metric_name in metric_names:
                group_score += (
                    float(normalized_metrics[model_key][metric_name])
                    * float(within_group_weights[metric_name])
                )
            group_scores[model_key][group_name] = float(group_score)
            total_scores[model_key] += float(group_score) * float(group_weight)

    ranked_models = sorted(
        model_keys,
        key=lambda model_key: (-total_scores[model_key], model_key),
    )
    winner = ranked_models[0] if ranked_models else None

    ranking = []
    for rank, model_key in enumerate(ranked_models, start=1):
        ranking.append(
            {
                "rank": rank,
                "model_key": model_key,
                "label": model_labels.get(model_key, model_key),
                "group_scores": group_scores[model_key],
                "composite_score": float(total_scores[model_key]),
            }
        )

    method_summary = {
        "timestamp": now_utc_iso(),
        "method": {
            "id": OPTION_2_SUBDIR,
            "name": OPTION_2_NAME,
            "mode": "grouped_primary_only",
        },
        "group_definitions": dict(OPTION_2_GROUP_DEFINITIONS),
        "within_group_weights": dict(OPTION_2_WITHIN_GROUP_WEIGHTS),
        "group_weights": dict(OPTION_2_GROUP_WEIGHTS),
        "winner": winner,
        "ranking": ranking,
        "artifacts": {
            "method_summary_json": str(output_dir / "method_summary.json"),
            "metric_snapshot_json": str(output_dir / "grouped_metric_snapshot.json"),
        },
    }

    metric_snapshot = {
        "raw_metrics": core_data["raw_metrics"],
        "normalized_metrics": core_data["normalized_metrics"],
        "group_scores": group_scores,
        "composite_scores": total_scores,
    }

    write_json(output_dir / "grouped_metric_snapshot.json", metric_snapshot)
    write_json(output_dir / "method_summary.json", method_summary)

    return {
        "method_id": OPTION_2_SUBDIR,
        "method_name": OPTION_2_NAME,
        "winner": winner,
        "ranking": [item["model_key"] for item in ranking],
        "group_definitions": dict(OPTION_2_GROUP_DEFINITIONS),
        "group_weights": dict(OPTION_2_GROUP_WEIGHTS),
        "group_scores": group_scores,
        "subfolder": str(output_dir),
        "method_summary_json": str(output_dir / "method_summary.json"),
    }


def run_option_3_direct_five_metric(
    *,
    core_data: dict[str, object],
    output_dir: Path,
    seed: int,
    sample_count: int,
    display_sample_count: int,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if display_sample_count <= 0:
        raise ValueError("display_sample_count must be positive")

    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    metric_names = core_data["metric_names"]
    normalized_metrics = core_data["normalized_metrics"]

    rng = np.random.default_rng(seed)
    weights = rng.dirichlet(alpha=np.ones(len(metric_names)), size=sample_count)

    matrix = np.array(
        [[normalized_metrics[model_key][metric_name] for metric_name in metric_names] for model_key in model_keys],
        dtype=float,
    )

    scores = matrix @ weights.T
    order = np.argsort(-scores, axis=0)

    rank_matrix = np.zeros_like(scores, dtype=int)
    for column in range(sample_count):
        rank_matrix[order[:, column], column] = np.arange(1, len(model_keys) + 1)

    winner_indices = order[0, :]
    winner_counts = np.bincount(winner_indices, minlength=len(model_keys))

    score_stats: dict[str, dict[str, float]] = {}
    winner_frequency: list[dict[str, object]] = []
    average_rank: list[dict[str, object]] = []

    for idx, model_key in enumerate(model_keys):
        model_scores = scores[idx, :]
        score_stats[model_key] = {
            "mean": float(np.mean(model_scores)),
            "std": float(np.std(model_scores)),
            "min": float(np.min(model_scores)),
            "max": float(np.max(model_scores)),
        }
        winner_frequency.append(
            {
                "model_key": model_key,
                "label": model_labels.get(model_key, model_key),
                "win_count": int(winner_counts[idx]),
                "win_rate": float(winner_counts[idx] / sample_count),
            }
        )
        average_rank.append(
            {
                "model_key": model_key,
                "label": model_labels.get(model_key, model_key),
                "average_rank": float(np.mean(rank_matrix[idx, :])),
            }
        )

    winner_frequency.sort(key=lambda row: (-row["win_count"], row["model_key"]))
    average_rank.sort(key=lambda row: (row["average_rank"], row["model_key"]))

    winner = winner_frequency[0]["model_key"] if winner_frequency else None
    ranking = [row["model_key"] for row in average_rank]

    preview_count = min(display_sample_count, sample_count)
    preview_weights = [
        {
            metric_names[metric_index]: float(weights[row_index, metric_index])
            for metric_index in range(len(metric_names))
        }
        for row_index in range(preview_count)
    ]

    method_summary = {
        "timestamp": now_utc_iso(),
        "method": {
            "id": OPTION_3_SUBDIR,
            "name": OPTION_3_NAME,
            "mode": "direct_flat_five_metric",
        },
        "metrics_used": list(metric_names),
        "metric_directions": dict(core_data["metric_directions"]),
        "seed": seed,
        "sample_count": sample_count,
        "display_sample_count": preview_count,
        "winner": winner,
        "winner_frequency": winner_frequency,
        "average_rank": average_rank,
        "ranking": ranking,
        "score_statistics": score_stats,
        "artifacts": {
            "method_summary_json": str(output_dir / "method_summary.json"),
            "weight_preview_json": str(output_dir / "option_3_weight_preview.json"),
            "metric_snapshot_json": str(output_dir / "option_3_metric_snapshot.json"),
        },
    }

    metric_snapshot = {
        "raw_metrics": core_data["raw_metrics"],
        "normalized_metrics": core_data["normalized_metrics"],
        "metric_sources": core_data["metric_sources"],
    }

    write_json(output_dir / "option_3_weight_preview.json", preview_weights)
    write_json(output_dir / "option_3_metric_snapshot.json", metric_snapshot)
    write_json(output_dir / "method_summary.json", method_summary)

    return {
        "method_id": OPTION_3_SUBDIR,
        "method_name": OPTION_3_NAME,
        "winner": winner,
        "ranking": ranking,
        "metrics_used": list(metric_names),
        "winner_frequency": winner_frequency,
        "average_rank": average_rank,
        "subfolder": str(output_dir),
        "method_summary_json": str(output_dir / "method_summary.json"),
    }


def model_rank_map(model_keys: list[str], ranking: list[str]) -> dict[str, int | None]:
    mapping = {model_key: None for model_key in model_keys}
    for rank, model_key in enumerate(ranking, start=1):
        mapping[model_key] = rank
    return mapping


def plot_ranked_lollipop(
    *,
    core_data: dict[str, object],
    option_results: list[dict[str, object]],
    output_path: Path,
) -> Path:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]

    per_method_ranks = [
        model_rank_map(model_keys, result["ranking"]) for result in option_results
    ]

    aggregate_ranks: dict[str, float] = {}
    for model_key in model_keys:
        valid_ranks = [rank_map[model_key] for rank_map in per_method_ranks if rank_map[model_key] is not None]
        if valid_ranks:
            aggregate_ranks[model_key] = float(np.mean(valid_ranks))
        else:
            aggregate_ranks[model_key] = float(len(model_keys) + 1)

    ordered_models = sorted(model_keys, key=lambda model_key: (aggregate_ranks[model_key], model_key))
    y_positions = np.arange(len(ordered_models))
    x_values = [aggregate_ranks[model_key] for model_key in ordered_models]
    labels = [model_labels.get(model_key, model_key) for model_key in ordered_models]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.hlines(y_positions, [0.0] * len(y_positions), x_values, color="#5D6D7E", linewidth=2)
    ax.scatter(x_values, y_positions, color="#C0392B", s=80, zorder=3)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Average rank across methods (lower is better)")
    ax.set_title("Figure 1: Ranked Lollipop Comparison")
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_metric_heatmap(
    *,
    core_data: dict[str, object],
    output_path: Path,
) -> Path:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    metric_names = core_data["metric_names"]
    normalized_metrics = core_data["normalized_metrics"]

    matrix = np.array(
        [[normalized_metrics[model_key][metric_name] for metric_name in metric_names] for model_key in model_keys],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(11, 4.5))
    image = ax.imshow(matrix, cmap="YlGnBu", vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_xticks(np.arange(len(metric_names)))
    ax.set_xticklabels(metric_names, rotation=20, ha="right")
    ax.set_yticks(np.arange(len(model_keys)))
    ax.set_yticklabels([model_labels.get(model_key, model_key) for model_key in model_keys])
    ax.set_title("Figure 2: Normalized Metric Heatmap")

    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            text_color = "black" if value < 0.70 else "white"
            ax.text(
                column_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=9,
            )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Normalized score")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def pareto_efficient_mask(x_values: np.ndarray, y_values: np.ndarray) -> np.ndarray:
    efficient = np.ones(x_values.shape[0], dtype=bool)
    for idx in range(x_values.shape[0]):
        if not efficient[idx]:
            continue
        dominated = (
            (x_values <= x_values[idx])
            & (y_values >= y_values[idx])
            & ((x_values < x_values[idx]) | (y_values > y_values[idx]))
        )
        dominated[idx] = False
        if np.any(dominated):
            efficient[idx] = False
    return efficient


def plot_latency_vs_recall_pareto(
    *,
    core_data: dict[str, object],
    output_path: Path,
) -> Path:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    raw_metrics = core_data["raw_metrics"]

    x_values = np.array([raw_metrics[model_key]["Inference Time"] for model_key in model_keys], dtype=float)
    y_values = np.array([raw_metrics[model_key]["Attack-Class Recall"] for model_key in model_keys], dtype=float)

    efficient_mask = pareto_efficient_mask(x_values, y_values)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(x_values, y_values, s=90, color="#34495E", alpha=0.85, label="All models")
    ax.scatter(
        x_values[efficient_mask],
        y_values[efficient_mask],
        s=130,
        facecolors="none",
        edgecolors="#E67E22",
        linewidths=2.0,
        label="Pareto-efficient",
    )

    for idx, model_key in enumerate(model_keys):
        ax.annotate(
            model_labels.get(model_key, model_key),
            (x_values[idx], y_values[idx]),
            textcoords="offset points",
            xytext=(6, 5),
            fontsize=9,
        )

    ax.set_xlabel("Inference Time (ms)")
    ax.set_ylabel("Attack-Class Recall")
    ax.set_title("Figure 3: Latency vs Recall (Pareto View)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_error_bars_across_seeds(
    *,
    core_data: dict[str, object],
    output_path: Path,
) -> Path:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    seed_error_metrics = core_data["seed_error_metrics"]

    fig, axes = plt.subplots(len(FIGURE_4_METRICS), 1, figsize=(10, 9), sharex=True)
    if len(FIGURE_4_METRICS) == 1:
        axes = [axes]

    x_positions = np.arange(len(model_keys))

    for axis, metric_name in zip(axes, FIGURE_4_METRICS):
        means = [seed_error_metrics[metric_name][model_key]["mean"] for model_key in model_keys]
        stds = [seed_error_metrics[metric_name][model_key]["std"] for model_key in model_keys]

        axis.errorbar(
            x_positions,
            means,
            yerr=stds,
            fmt="o",
            color="#1F618D",
            ecolor="#117A65",
            elinewidth=1.8,
            capsize=5,
        )
        axis.set_ylabel(metric_name)
        axis.grid(alpha=0.3)

    axes[-1].set_xticks(x_positions)
    axes[-1].set_xticklabels([model_labels.get(model_key, model_key) for model_key in model_keys], rotation=15, ha="right")
    fig.suptitle("Figure 4: Error Bars Across Seeds", y=0.995)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_profile_radar(
    *,
    model_keys: list[str],
    model_labels: dict[str, str],
    axis_names: list[str],
    profile_values: dict[str, dict[str, float]],
    output_path: Path,
    title: str,
    subtitle: str | None = None,
    legend_labels: dict[str, str] | None = None,
) -> Path:
    theta = np.linspace(0.0, 2 * np.pi, len(axis_names), endpoint=False)
    closed_theta = np.append(theta, theta[0])

    if len(axis_names) <= 3:
        figure_size = (11, 11)
    else:
        figure_size = (12, 12)

    fig, ax = plt.subplots(figsize=figure_size, subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor("#f7f7f7")
    ax.set_facecolor("#f7f7f7")

    for model_key in model_keys:
        values = [float(profile_values[model_key][axis_name]) for axis_name in axis_names]
        closed_values = np.append(np.array(values, dtype=float), values[0])
        label = (
            legend_labels[model_key]
            if legend_labels is not None and model_key in legend_labels
            else model_labels.get(model_key, model_key)
        )
        ax.plot(closed_theta, closed_values, linewidth=2, label=label)
        # Keep a line-forward engineering style; avoid heavy polygon fill.
        ax.fill(closed_theta, closed_values, alpha=0.02)

    ax.set_xticks(theta)
    ax.set_xticklabels(axis_names, fontsize=14)
    ax.tick_params(axis="x", pad=18)
    ax.set_ylim(0.0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=11)
    ax.set_yticks(np.arange(0.05, 1.0, 0.05), minor=True)
    ax.set_rlabel_position(22.5)
    ax.grid(True, which="major", color="#8f8f8f", alpha=0.55, linewidth=1.0)
    ax.grid(True, which="minor", color="#b6b6b6", alpha=0.50, linewidth=0.65)
    ax.spines["polar"].set_linewidth(2.2)
    ax.spines["polar"].set_color("#4f4f4f")
    fig.suptitle(title, y=0.97, fontsize=22, fontweight="semibold")
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.18, 1.12),
        frameon=True,
        framealpha=0.95,
        fontsize=12,
    )

    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", va="center", fontsize=11)

    fig.tight_layout(rect=[0.03, 0.07, 0.97, 0.91])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def build_option_1_tier_map(
    *,
    option_1_result: dict[str, object],
    model_keys: list[str],
) -> dict[str, str]:
    tier_map = {model_key: "ineligible" for model_key in model_keys}
    for model_key in option_1_result.get("conditionally_eligible_models", []):
        if model_key in tier_map:
            tier_map[model_key] = "conditionally_eligible"
    for model_key in option_1_result.get("preferred_models", []):
        if model_key in tier_map:
            tier_map[model_key] = "preferred"
    return tier_map


def plot_option_1_radar(
    *,
    core_data: dict[str, object],
    option_1_result: dict[str, object],
    output_path: Path,
) -> tuple[Path, dict[str, object]]:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    normalized_metrics = core_data["normalized_metrics"]

    tier_map = build_option_1_tier_map(option_1_result=option_1_result, model_keys=model_keys)
    legend_labels = {
        model_key: f"{model_labels.get(model_key, model_key)} ({tier_map[model_key]})"
        for model_key in model_keys
    }

    path = plot_profile_radar(
        model_keys=model_keys,
        model_labels=model_labels,
        axis_names=list(METRIC_NAMES),
        profile_values=normalized_metrics,
        output_path=output_path,
        title="Figure 5: Option 1 Gate Profile Radar (5-Metric)",
        subtitle="Tier labels included in legend: preferred / conditionally_eligible / ineligible",
        legend_labels=legend_labels,
    )
    metadata = {
        "axes": list(METRIC_NAMES),
        "source": "core_normalized_metrics",
        "view": "option_1_gate_profile",
        "tiers": tier_map,
        "style_version": RADAR_STYLE_VERSION,
    }
    return path, metadata


def plot_option_2_radar(
    *,
    core_data: dict[str, object],
    option_2_result: dict[str, object],
    output_path: Path,
) -> tuple[Path, dict[str, object]]:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    axis_names = list(OPTION_2_GROUP_DEFINITIONS.keys())
    group_scores = option_2_result["group_scores"]

    path = plot_profile_radar(
        model_keys=model_keys,
        model_labels=model_labels,
        axis_names=axis_names,
        profile_values=group_scores,
        output_path=output_path,
        title="Figure 6: Option 2 Grouped Radar (Security / Efficiency / Training Practicality)",
        subtitle="Grouped view uses Option 2 group scores (not flat five-metric axes)",
    )
    metadata = {
        "axes": axis_names,
        "source": "option_2_group_scores",
        "view": "option_2_grouped_profile",
        "style_version": RADAR_STYLE_VERSION,
    }
    return path, metadata


def plot_option_3_radar(
    *,
    core_data: dict[str, object],
    output_path: Path,
) -> tuple[Path, dict[str, object]]:
    model_keys = core_data["model_keys"]
    model_labels = core_data["model_labels"]
    normalized_metrics = core_data["normalized_metrics"]

    path = plot_profile_radar(
        model_keys=model_keys,
        model_labels=model_labels,
        axis_names=list(METRIC_NAMES),
        profile_values=normalized_metrics,
        output_path=output_path,
        title="Figure 7: Option 3 Flat Five-Metric Radar",
        subtitle="Flat five-metric normalized profile view",
    )
    metadata = {
        "axes": list(METRIC_NAMES),
        "source": "core_normalized_metrics",
        "view": "option_3_flat_five_metric_profile",
        "style_version": RADAR_STYLE_VERSION,
    }
    return path, metadata


def write_parent_outputs(
    *,
    parent_dir: Path,
    run_dir: Path,
    core_data: dict[str, object],
    option_1_result: dict[str, object],
    option_2_result: dict[str, object],
    option_3_result: dict[str, object],
    figure_paths: dict[str, Path],
    figure_metadata: dict[str, dict[str, object]],
) -> tuple[Path, Path]:
    combined_summary_path = parent_dir / "combined_method_comparison_summary.json"
    comparison_table_path = parent_dir / "method_comparison_table.json"

    method_results = [option_1_result, option_2_result, option_3_result]

    combined_summary_payload = {
        "timestamp": now_utc_iso(),
        "source_run_path": str(run_dir),
        "method_names": [OPTION_1_NAME, OPTION_2_NAME, OPTION_3_NAME],
        "method_subfolders": {
            OPTION_1_SUBDIR: str(parent_dir / OPTION_1_SUBDIR),
            OPTION_2_SUBDIR: str(parent_dir / OPTION_2_SUBDIR),
            OPTION_3_SUBDIR: str(parent_dir / OPTION_3_SUBDIR),
        },
        "core_metrics": {
            "metric_names": core_data["metric_names"],
            "metric_directions": core_data["metric_directions"],
            "metric_sources": core_data["metric_sources"],
        },
        "methods": method_results,
        "parent_figures": {
            "figure_1_ranked_lollipop_png": str(figure_paths[FIGURE_1_NAME]),
            "figure_2_metric_heatmap_png": str(figure_paths[FIGURE_2_NAME]),
            "figure_3_latency_vs_recall_pareto_png": str(figure_paths[FIGURE_3_NAME]),
            "figure_4_error_bars_across_seeds_png": str(figure_paths[FIGURE_4_NAME]),
            "figure_5_option_1_radar_png": str(figure_paths[FIGURE_5_NAME]),
            "figure_6_option_2_radar_png": str(figure_paths[FIGURE_6_NAME]),
            "figure_7_option_3_radar_png": str(figure_paths[FIGURE_7_NAME]),
        },
        "parent_figure_metadata": figure_metadata,
    }

    option_1_rank_map = model_rank_map(core_data["model_keys"], option_1_result["ranking"])
    option_2_rank_map = model_rank_map(core_data["model_keys"], option_2_result["ranking"])
    option_3_rank_map = model_rank_map(core_data["model_keys"], option_3_result["ranking"])

    rows = []
    for model_key in core_data["model_keys"]:
        rows.append(
            {
                "model_key": model_key,
                "label": core_data["model_labels"].get(model_key, model_key),
                "option_1_rank": option_1_rank_map[model_key],
                "option_2_rank": option_2_rank_map[model_key],
                "option_3_rank": option_3_rank_map[model_key],
            }
        )

    comparison_table_payload = {
        "timestamp": combined_summary_payload["timestamp"],
        "source_run_path": str(run_dir),
        "winner_by_method": {
            option_1_result["method_name"]: option_1_result["winner"],
            option_2_result["method_name"]: option_2_result["winner"],
            option_3_result["method_name"]: option_3_result["winner"],
        },
        "ranking_by_method": {
            option_1_result["method_name"]: option_1_result["ranking"],
            option_2_result["method_name"]: option_2_result["ranking"],
            option_3_result["method_name"]: option_3_result["ranking"],
        },
        "rows": rows,
    }

    write_json(combined_summary_path, combined_summary_payload)
    write_json(comparison_table_path, comparison_table_payload)

    return combined_summary_path, comparison_table_path


def create_parent_output_dir(output_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parent_dir = output_root / f"method_comparison_fresh_{timestamp}"
    parent_dir.mkdir(parents=True, exist_ok=False)
    return parent_dir


def run_fresh_method_comparison(
    *,
    run_dir: Path | None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    seed: int = DEFAULT_RANDOM_SEED,
    option_3_sample_count: int = DEFAULT_OPTION_3_SAMPLE_COUNT,
    option_3_display_sample_count: int = DEFAULT_OPTION_3_DISPLAY_SAMPLE_COUNT,
    gate_policy: GatePolicy | None = None,
) -> dict[str, object]:
    resolved_run_dir = run_dir if run_dir is not None else find_latest_valid_run_dir(results_root)
    resolved_gate_policy = gate_policy if gate_policy is not None else GatePolicy()

    parent_dir = create_parent_output_dir(output_root)

    core_data = build_core_metric_data(resolved_run_dir)

    option_1_dir = parent_dir / OPTION_1_SUBDIR
    option_2_dir = parent_dir / OPTION_2_SUBDIR
    option_3_dir = parent_dir / OPTION_3_SUBDIR

    option_1_result = run_option_1_security_gate(
        core_data=core_data,
        output_dir=option_1_dir,
        gate_policy=resolved_gate_policy,
    )
    option_2_result = run_option_2_grouped_weighting(
        core_data=core_data,
        output_dir=option_2_dir,
    )
    option_3_result = run_option_3_direct_five_metric(
        core_data=core_data,
        output_dir=option_3_dir,
        seed=seed,
        sample_count=option_3_sample_count,
        display_sample_count=option_3_display_sample_count,
    )

    figure_paths = {
        FIGURE_1_NAME: plot_ranked_lollipop(
            core_data=core_data,
            option_results=[option_1_result, option_2_result, option_3_result],
            output_path=parent_dir / FIGURE_1_NAME,
        ),
        FIGURE_2_NAME: plot_metric_heatmap(
            core_data=core_data,
            output_path=parent_dir / FIGURE_2_NAME,
        ),
        FIGURE_3_NAME: plot_latency_vs_recall_pareto(
            core_data=core_data,
            output_path=parent_dir / FIGURE_3_NAME,
        ),
        FIGURE_4_NAME: plot_error_bars_across_seeds(
            core_data=core_data,
            output_path=parent_dir / FIGURE_4_NAME,
        ),
    }

    option_1_radar_path, option_1_radar_metadata = plot_option_1_radar(
        core_data=core_data,
        option_1_result=option_1_result,
        output_path=parent_dir / FIGURE_5_NAME,
    )
    option_2_radar_path, option_2_radar_metadata = plot_option_2_radar(
        core_data=core_data,
        option_2_result=option_2_result,
        output_path=parent_dir / FIGURE_6_NAME,
    )
    option_3_radar_path, option_3_radar_metadata = plot_option_3_radar(
        core_data=core_data,
        output_path=parent_dir / FIGURE_7_NAME,
    )

    figure_paths[FIGURE_5_NAME] = option_1_radar_path
    figure_paths[FIGURE_6_NAME] = option_2_radar_path
    figure_paths[FIGURE_7_NAME] = option_3_radar_path

    figure_metadata = {
        "figure_5_option_1_radar": option_1_radar_metadata,
        "figure_6_option_2_radar": option_2_radar_metadata,
        "figure_7_option_3_radar": option_3_radar_metadata,
    }

    combined_summary_path, comparison_table_path = write_parent_outputs(
        parent_dir=parent_dir,
        run_dir=resolved_run_dir,
        core_data=core_data,
        option_1_result=option_1_result,
        option_2_result=option_2_result,
        option_3_result=option_3_result,
        figure_paths=figure_paths,
        figure_metadata=figure_metadata,
    )

    return {
        "parent_dir": str(parent_dir),
        "source_run_dir": str(resolved_run_dir),
        "option_1": option_1_result,
        "option_2": option_2_result,
        "option_3": option_3_result,
        "combined_summary_json": str(combined_summary_path),
        "comparison_table_json": str(comparison_table_path),
        "parent_figures": {name: str(path) for name, path in figure_paths.items()},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a fresh three-method sensitivity comparison workflow and write a clean "
            "parent comparison package."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        help=(
            "Optional benchmark run directory. If omitted, latest valid run under "
            "--results-root is used."
        ),
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help=f"Results root for run discovery. Default: {DEFAULT_RESULTS_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output root for fresh comparison runs. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help=f"Random seed for stochastic methods. Default: {DEFAULT_RANDOM_SEED}",
    )
    parser.add_argument(
        "--option-3-sample-count",
        type=int,
        default=DEFAULT_OPTION_3_SAMPLE_COUNT,
        help=f"Direct five-metric sample count. Default: {DEFAULT_OPTION_3_SAMPLE_COUNT}",
    )
    parser.add_argument(
        "--option-3-display-sample-count",
        type=int,
        default=DEFAULT_OPTION_3_DISPLAY_SAMPLE_COUNT,
        help=(
            "Stored preview sample count from weight draws. "
            f"Default: {DEFAULT_OPTION_3_DISPLAY_SAMPLE_COUNT}"
        ),
    )
    parser.add_argument(
        "--minimum-acceptable-min-attack-class-recall",
        type=float,
        default=OPTION_1_MINIMUM_ACCEPTABLE["min_attack_class_recall"],
        help=(
            "Option 1 minimum acceptable gate: minimum Attack-Class Recall. "
            "Default: 0.990"
        ),
    )
    parser.add_argument(
        "--minimum-acceptable-max-normal-fpr",
        type=float,
        default=OPTION_1_MINIMUM_ACCEPTABLE["max_normal_false_positive_rate"],
        help=(
            "Option 1 minimum acceptable gate: maximum Normal False Positive Rate. "
            "Default: 0.010"
        ),
    )
    parser.add_argument(
        "--preferred-min-attack-class-recall",
        type=float,
        default=OPTION_1_PREFERRED["min_attack_class_recall"],
        help=(
            "Option 1 preferred gate: minimum Attack-Class Recall. Default: 0.994"
        ),
    )
    parser.add_argument(
        "--preferred-max-normal-fpr",
        type=float,
        default=OPTION_1_PREFERRED["max_normal_false_positive_rate"],
        help=(
            "Option 1 preferred gate: maximum Normal False Positive Rate. Default: 0.005"
        ),
    )
    parser.add_argument(
        "--operational-max-inference-time-ms",
        type=float,
        default=OPTION_1_OPERATIONAL_CONSTRAINT["max_inference_time_ms"],
        help=(
            "Option 1 operational latency constraint in ms (not a co-equal security gate). "
            "Default: 50"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = run_fresh_method_comparison(
        run_dir=args.run_dir,
        output_root=args.output_root,
        results_root=args.results_root,
        seed=args.seed,
        option_3_sample_count=args.option_3_sample_count,
        option_3_display_sample_count=args.option_3_display_sample_count,
        gate_policy=GatePolicy(
            minimum_acceptable_min_attack_class_recall=args.minimum_acceptable_min_attack_class_recall,
            minimum_acceptable_max_normal_false_positive_rate=args.minimum_acceptable_max_normal_fpr,
            preferred_min_attack_class_recall=args.preferred_min_attack_class_recall,
            preferred_max_normal_false_positive_rate=args.preferred_max_normal_fpr,
            operational_max_inference_time_ms=args.operational_max_inference_time_ms,
            zero_pass_behavior="no_ranking",
        ),
    )

    print(f"Source run: {result['source_run_dir']}")
    print(f"Parent output: {result['parent_dir']}")
    print("\nMethod winners:")
    print(f"- {OPTION_1_NAME}: {result['option_1']['winner']}")
    print(f"- {OPTION_2_NAME}: {result['option_2']['winner']}")
    print(f"- {OPTION_3_NAME}: {result['option_3']['winner']}")
    print("\nOutput paths:")
    print(f"- combined_summary_json: {result['combined_summary_json']}")
    print(f"- comparison_table_json: {result['comparison_table_json']}")
    for figure_name, figure_path in result["parent_figures"].items():
        print(f"- {figure_name}: {figure_path}")


if __name__ == "__main__":
    main()
