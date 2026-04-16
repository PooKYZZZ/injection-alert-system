from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = (
    REPO_ROOT
    / "ml_model"
    / "notebooks"
    / "training done"
    / "Final training"
    / "results"
)
DEFAULT_BENCHMARK_SUMMARY_NAME = "model_benchmark_summary.csv"
DEFAULT_EVALUATION_SUMMARY_RELATIVE_PATH = Path("evaluation") / "final_model_comparison.csv"
DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH = Path("evaluation") / "aggregated_per_class_summary.csv"
DEFAULT_OUTPUT_ROOT = Path("artifacts") / "sensitivity_analysis_runs"

DEFAULT_MODEL_ORDER = (
    "tinybert_bigru_attn",
    "distilbert",
    "minilm_l6",
)

DEFAULT_DESIGN_LABELS = {
    "tinybert_bigru_attn": "Model A: TinyBERT BiGRU Attention",
    "distilbert": "Model B: DistilBERT",
    "minilm_l6": "Model C: MiniLM-L6",
}

TOP_LEVEL_DECISION_CRITERIA = (
    "Attack-Class Recall",
    "Normal False Positive Rate",
    "Inference Time",
    "Model Size",
    "Training Runtime",
)

SECONDARY_METRICS_EXCLUDED_FROM_TOP_LEVEL = (
    "Macro F1",
    "Per-class precision/recall/F1",
    "Confusion matrix",
    "ECE",
    "Brier",
    "NLL",
    "Reliability diagrams",
    "Threshold analysis",
)

REQUIRED_GROUPS = (
    "Security",
    "Efficiency",
)

BASE_SCENARIO_GROUP_WEIGHTS = {
    "Security-First": {
        "Security": 0.65,
        "Efficiency": 0.35,
    },
    "Balanced": {
        "Security": 0.50,
        "Efficiency": 0.50,
    },
    "Efficiency-Aware": {
        "Security": 0.35,
        "Efficiency": 0.65,
    },
}

DEFAULT_STABILITY_GROUP_WEIGHT = 0.10
DEFAULT_SEED = 135
DEFAULT_CONSTRAINED_SAMPLES = 10000
DEFAULT_UNCONSTRAINED_SAMPLES = 10000
DEFAULT_SECURITY_DOMINANCE_MARGIN = 0.02
DEFAULT_PLOT_SAMPLE_COUNT = 150


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def rows_by_model(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        model_key = row.get("model_key")
        if model_key:
            output[model_key] = row
    return output


def find_latest_run_dir(results_root: Path) -> Path:
    if not results_root.exists():
        raise FileNotFoundError(f"Results root does not exist: {results_root}")

    candidates = [
        candidate
        for candidate in results_root.iterdir()
        if candidate.is_dir() and (candidate / DEFAULT_BENCHMARK_SUMMARY_NAME).exists()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No final benchmark runs found under results root: {results_root}"
        )

    return max(candidates, key=lambda candidate: candidate.stat().st_mtime)


def infer_model_order(model_keys: list[str]) -> list[str]:
    ordered = [model_key for model_key in DEFAULT_MODEL_ORDER if model_key in model_keys]
    remaining = sorted(model_key for model_key in model_keys if model_key not in ordered)
    return ordered + remaining


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
    for row, source_path in ((primary_row, primary_path), (secondary_row, secondary_path)):
        if row is None:
            continue
        raw = row.get(field_name)
        if raw not in (None, ""):
            return float(raw)

    searched = [str(path) for path in (primary_path, secondary_path) if path is not None]
    raise ValueError(
        f"Missing required field '{field_name}' in source files: {', '.join(searched)}"
    )


def preferred_field_available(
    model_keys: list[str],
    evaluation_rows: dict[str, dict[str, str]],
    benchmark_rows: dict[str, dict[str, str]],
    field_name: str,
) -> bool:
    for model_key in model_keys:
        eval_row = evaluation_rows.get(model_key)
        benchmark_row = benchmark_rows.get(model_key)
        found = False
        for row in (eval_row, benchmark_row):
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
) -> dict[str, float] | None:
    if not per_class_path.exists():
        return None

    rows = [
        row
        for row in load_csv_rows(per_class_path)
        if row.get("model_key") in model_keys
    ]
    if not rows:
        return None

    by_model: dict[str, list[float]] = {model_key: [] for model_key in model_keys}
    for row in rows:
        label_name = (row.get("label_name") or "").strip().lower()
        if label_name == "normal":
            continue

        recall_raw = row.get("recall_mean")
        if recall_raw in (None, ""):
            return None

        by_model[row["model_key"]].append(float(recall_raw))

    if any(len(values) == 0 for values in by_model.values()):
        return None

    return {model_key: float(mean(values)) for model_key, values in by_model.items()}


def build_decision_data_from_run(
    run_dir: Path,
    *,
    include_stability_group: bool,
) -> dict:
    benchmark_path = run_dir / DEFAULT_BENCHMARK_SUMMARY_NAME
    evaluation_path = run_dir / DEFAULT_EVALUATION_SUMMARY_RELATIVE_PATH
    per_class_path = run_dir / DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH

    benchmark_rows = rows_by_model(load_csv_rows(benchmark_path))
    evaluation_rows = (
        rows_by_model(load_csv_rows(evaluation_path))
        if evaluation_path.exists()
        else {}
    )

    model_keys = infer_model_order(list(benchmark_rows))
    if not model_keys:
        raise ValueError(f"No model rows found in benchmark summary: {benchmark_path}")

    raw_metrics: dict[str, dict[str, float]] = {model_key: {} for model_key in model_keys}
    metric_definitions: dict[str, dict[str, object]] = {}
    group_metrics: dict[str, list[str]] = {group: [] for group in REQUIRED_GROUPS}

    def add_metric(
        group_name: str,
        metric_name: str,
        *,
        maximize: bool,
        values_by_model: dict[str, float],
        source_detail: str,
    ) -> None:
        group_metrics[group_name].append(metric_name)
        metric_definitions[metric_name] = {
            "group": group_name,
            "maximize": maximize,
            "source": source_detail,
        }
        for model_key in model_keys:
            raw_metrics[model_key][metric_name] = values_by_model[model_key]

    attack_class_recall = compute_attack_class_recall(per_class_path, model_keys)
    if attack_class_recall is None:
        raise ValueError(
            f"Missing attack-class recall data in {per_class_path}. "
            "Top-level sensitivity criteria require Attack-Class Recall."
        )
    add_metric(
        "Security",
        "Attack-Class Recall",
        maximize=True,
        values_by_model=attack_class_recall,
        source_detail=f"{DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH}: recall_mean over non-Normal labels",
    )

    add_metric(
        "Security",
        "Normal False Positive Rate",
        maximize=False,
        values_by_model=extract_metric_values(
            model_keys,
            evaluation_rows,
            benchmark_rows,
            "normal_false_positive_rate_mean",
            evaluation_path=evaluation_path if evaluation_path.exists() else None,
            benchmark_path=benchmark_path,
        ),
        source_detail="normal_false_positive_rate_mean",
    )

    if preferred_field_available(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_p95_ms_mean",
    ):
        inference_time_field = "inference_latency_p95_ms_mean"
    elif preferred_field_available(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_p50_ms_mean",
    ):
        inference_time_field = "inference_latency_p50_ms_mean"
    elif preferred_field_available(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "inference_latency_mean_ms_mean",
    ):
        inference_time_field = "inference_latency_mean_ms_mean"
    else:
        raise ValueError(
            "Missing inference time fields: expected one of "
            "inference_latency_p95_ms_mean, inference_latency_p50_ms_mean, "
            "or inference_latency_mean_ms_mean"
        )

    add_metric(
        "Efficiency",
        "Inference Time",
        maximize=False,
        values_by_model=extract_metric_values(
            model_keys,
            evaluation_rows,
            benchmark_rows,
            inference_time_field,
            evaluation_path=evaluation_path if evaluation_path.exists() else None,
            benchmark_path=benchmark_path,
        ),
        source_detail=inference_time_field,
    )

    model_size_values: dict[str, float] = {}
    for model_key in model_keys:
        model_size_values[model_key] = parse_required_float(
            benchmark_rows[model_key],
            "model_size_mb_mean",
            source_path=benchmark_path,
        )
    add_metric(
        "Efficiency",
        "Model Size",
        maximize=False,
        values_by_model=model_size_values,
        source_detail="model_size_mb_mean",
    )

    add_metric(
        "Efficiency",
        "Training Runtime",
        maximize=False,
        values_by_model=extract_metric_values(
            model_keys,
            evaluation_rows,
            benchmark_rows,
            "training_workflow_runtime_sec_mean",
            evaluation_path=evaluation_path if evaluation_path.exists() else None,
            benchmark_path=benchmark_path,
        ),
        source_detail="training_workflow_runtime_sec_mean",
    )

    _ = include_stability_group
    stability_group_active = False

    return {
        "model_keys": model_keys,
        "raw_metrics": raw_metrics,
        "group_metrics": group_metrics,
        "metric_definitions": metric_definitions,
        "benchmark_path": benchmark_path,
        "evaluation_path": evaluation_path if evaluation_path.exists() else None,
        "per_class_path": per_class_path if per_class_path.exists() else None,
        "stability_group_active": stability_group_active,
    }


def build_within_group_weights(group_metrics: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    weights: dict[str, dict[str, float]] = {}
    for group_name, metrics in group_metrics.items():
        if not metrics:
            continue
        equal_weight = 1.0 / len(metrics)
        weights[group_name] = {metric: equal_weight for metric in metrics}

    return weights


def normalize_values(
    values_by_model: dict[str, float],
    *,
    maximize: bool,
) -> dict[str, float]:
    min_value = min(values_by_model.values())
    max_value = max(values_by_model.values())
    if max_value == min_value:
        return {model_key: 1.0 for model_key in values_by_model}

    if maximize:
        return {
            model_key: (value - min_value) / (max_value - min_value)
            for model_key, value in values_by_model.items()
        }

    return {
        model_key: (max_value - value) / (max_value - min_value)
        for model_key, value in values_by_model.items()
    }


def normalize_metrics(
    raw_metrics: dict[str, dict[str, float]],
    metric_definitions: dict[str, dict[str, object]],
) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {
        model_key: {} for model_key in raw_metrics
    }

    for metric_name, definition in metric_definitions.items():
        maximize = bool(definition["maximize"])
        metric_values = {
            model_key: metrics[metric_name]
            for model_key, metrics in raw_metrics.items()
        }
        scaled_values = normalize_values(metric_values, maximize=maximize)
        for model_key, scaled in scaled_values.items():
            normalized[model_key][metric_name] = scaled

    return normalized


def compute_group_scores(
    normalized_metrics: dict[str, dict[str, float]],
    group_metrics: dict[str, list[str]],
    within_group_weights: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    group_scores: dict[str, dict[str, float]] = {
        model_key: {} for model_key in normalized_metrics
    }

    for model_key, metrics in normalized_metrics.items():
        for group_name, metric_names in group_metrics.items():
            if not metric_names:
                continue
            group_score = sum(
                metrics[metric_name] * within_group_weights[group_name][metric_name]
                for metric_name in metric_names
            )
            group_scores[model_key][group_name] = group_score

    return group_scores


def build_scenario_group_weights(
    group_metrics: dict[str, list[str]],
    *,
    stability_group_active: bool,
    stability_group_weight: float,
) -> dict[str, dict[str, float]]:
    missing_groups = [group for group in REQUIRED_GROUPS if group not in group_metrics]
    if missing_groups:
        missing_display = ", ".join(missing_groups)
        raise ValueError(f"Missing required decision groups: {missing_display}")

    scenarios: dict[str, dict[str, float]] = {}
    for scenario_name, base_weights in BASE_SCENARIO_GROUP_WEIGHTS.items():
        if stability_group_active:
            if not (0.0 < stability_group_weight < 0.5):
                raise ValueError("stability_group_weight must be in (0.0, 0.5)")
            scale = 1.0 - stability_group_weight
            weights = {
                group_name: base_weights[group_name] * scale
                for group_name in REQUIRED_GROUPS
            }
            weights["Stability"] = stability_group_weight
        else:
            weights = {
                group_name: base_weights[group_name]
                for group_name in REQUIRED_GROUPS
            }

        total_weight = sum(weights.values())
        normalized = {
            group_name: weight / total_weight
            for group_name, weight in weights.items()
        }
        scenarios[scenario_name] = normalized

    return scenarios


def compute_composite_scores(
    group_scores: dict[str, dict[str, float]],
    group_weights: dict[str, float],
) -> dict[str, float]:
    return {
        model_key: sum(
            scores[group_name] * group_weights[group_name]
            for group_name in group_weights
        )
        for model_key, scores in group_scores.items()
    }


def rank_models(scores_by_model: dict[str, float]) -> list[str]:
    return sorted(
        scores_by_model,
        key=lambda model_key: (-scores_by_model[model_key], model_key),
    )


def evaluate_scenarios(
    group_scores: dict[str, dict[str, float]],
    scenario_group_weights: dict[str, dict[str, float]],
    design_labels: dict[str, str],
) -> list[dict[str, object]]:
    scenario_results: list[dict[str, object]] = []

    for scenario_name, group_weights in scenario_group_weights.items():
        composite_scores = compute_composite_scores(group_scores, group_weights)
        ranked_models = rank_models(composite_scores)
        winner = ranked_models[0]
        ranking_rows = []
        for rank, model_key in enumerate(ranked_models, start=1):
            ranking_rows.append(
                {
                    "rank": rank,
                    "model_key": model_key,
                    "label": design_labels.get(model_key, model_key),
                    "composite_score": float(composite_scores[model_key]),
                    "group_scores": {
                        group_name: float(group_scores[model_key][group_name])
                        for group_name in group_weights
                    },
                }
            )

        scenario_results.append(
            {
                "scenario": scenario_name,
                "group_weights": {
                    group_name: float(group_weights[group_name])
                    for group_name in group_weights
                },
                "winner_model_key": winner,
                "winner_label": design_labels.get(winner, winner),
                "ranking": ranking_rows,
            }
        )

    return scenario_results


def sample_group_weights(group_names: list[str], rng: random.Random) -> dict[str, float]:
    draws = [rng.gammavariate(1.0, 1.0) for _ in group_names]
    total = sum(draws)
    return {
        group_name: draw / total
        for group_name, draw in zip(group_names, draws)
    }


def is_constrained_weight_sample(
    weights: dict[str, float],
    *,
    security_margin: float,
) -> bool:
    security_weight = weights.get("Security", 0.0)
    efficiency_weight = weights.get("Efficiency", 0.0)

    if security_weight <= efficiency_weight:
        return False
    if (security_weight - efficiency_weight) < security_margin:
        return False

    for group_name, value in weights.items():
        if group_name == "Security":
            continue
        if security_weight < value:
            return False

    return True


def generate_weight_samples(
    group_names: list[str],
    *,
    sample_count: int,
    rng: random.Random,
    constrained: bool,
    security_margin: float,
) -> tuple[list[dict[str, float]], int]:
    if sample_count <= 0:
        raise ValueError("sample_count must be > 0")

    samples: list[dict[str, float]] = []
    attempts = 0
    max_attempts = sample_count * 500

    while len(samples) < sample_count:
        attempts += 1
        if constrained and attempts > max_attempts:
            raise RuntimeError(
                "Unable to generate enough constrained samples. "
                "Try reducing security_dominance_margin or sample_count."
            )

        sample = sample_group_weights(group_names, rng)
        if constrained and not is_constrained_weight_sample(
            sample,
            security_margin=security_margin,
        ):
            continue

        samples.append(sample)

    return samples, attempts


def summarize_weight_distribution(
    weight_samples: list[dict[str, float]],
) -> dict[str, dict[str, float]]:
    group_names = list(weight_samples[0])
    summary: dict[str, dict[str, float]] = {}
    for group_name in group_names:
        values = [sample[group_name] for sample in weight_samples]
        summary[group_name] = {
            "mean": float(mean(values)),
            "min": float(min(values)),
            "max": float(max(values)),
        }
    return summary


def summarize_weight_sampling(
    group_scores: dict[str, dict[str, float]],
    weight_samples: list[dict[str, float]],
    design_labels: dict[str, str],
) -> dict[str, object]:
    model_keys = list(group_scores)
    rank_positions = list(range(1, len(model_keys) + 1))

    winner_counts = {model_key: 0 for model_key in model_keys}
    rank_counts = {
        model_key: {rank: 0 for rank in rank_positions}
        for model_key in model_keys
    }
    rank_sums = {model_key: 0.0 for model_key in model_keys}
    score_series = {model_key: [] for model_key in model_keys}

    for weights in weight_samples:
        scores = compute_composite_scores(group_scores, weights)
        ranked_models = rank_models(scores)
        winner_counts[ranked_models[0]] += 1

        for rank, model_key in enumerate(ranked_models, start=1):
            rank_counts[model_key][rank] += 1
            rank_sums[model_key] += rank

        for model_key, score in scores.items():
            score_series[model_key].append(score)

    sample_count = len(weight_samples)

    winner_frequency = [
        {
            "model_key": model_key,
            "label": design_labels.get(model_key, model_key),
            "wins": int(winner_counts[model_key]),
            "win_rate": float(winner_counts[model_key] / sample_count),
        }
        for model_key in model_keys
    ]
    winner_frequency.sort(key=lambda item: (-int(item["wins"]), str(item["model_key"])))

    rank_frequency = []
    average_rank = []
    score_stats = []
    for model_key in model_keys:
        count_map = {
            str(rank): int(rank_counts[model_key][rank])
            for rank in rank_positions
        }
        rate_map = {
            str(rank): float(rank_counts[model_key][rank] / sample_count)
            for rank in rank_positions
        }
        avg_rank = float(rank_sums[model_key] / sample_count)

        rank_frequency.append(
            {
                "model_key": model_key,
                "label": design_labels.get(model_key, model_key),
                "rank_counts": count_map,
                "rank_rates": rate_map,
                "average_rank": avg_rank,
            }
        )
        average_rank.append(
            {
                "model_key": model_key,
                "label": design_labels.get(model_key, model_key),
                "average_rank": avg_rank,
            }
        )
        score_stats.append(
            {
                "model_key": model_key,
                "label": design_labels.get(model_key, model_key),
                "mean_score": float(mean(score_series[model_key])),
                "min_score": float(min(score_series[model_key])),
                "max_score": float(max(score_series[model_key])),
            }
        )

    rank_frequency.sort(
        key=lambda item: (float(item["average_rank"]), str(item["model_key"]))
    )
    average_rank.sort(
        key=lambda item: (float(item["average_rank"]), str(item["model_key"]))
    )
    score_stats.sort(
        key=lambda item: (-float(item["mean_score"]), str(item["model_key"]))
    )

    return {
        "sample_count": sample_count,
        "winner_frequency": winner_frequency,
        "rank_frequency": rank_frequency,
        "average_rank": average_rank,
        "score_stats": score_stats,
        "weight_distribution": summarize_weight_distribution(weight_samples),
    }


def compute_score_series(
    group_scores: dict[str, dict[str, float]],
    weight_samples: list[dict[str, float]],
) -> dict[str, list[float]]:
    score_series = {model_key: [] for model_key in group_scores}
    for weights in weight_samples:
        scores = compute_composite_scores(group_scores, weights)
        for model_key, score in scores.items():
            score_series[model_key].append(score)
    return score_series


def select_display_indices(total_count: int, max_points: int) -> list[int]:
    if total_count <= 0:
        raise ValueError("total_count must be > 0")
    if max_points <= 0:
        raise ValueError("max_points must be > 0")

    if total_count <= max_points:
        return list(range(total_count))
    if max_points == 1:
        return [0]

    return [
        (i * (total_count - 1)) // (max_points - 1)
        for i in range(max_points)
    ]


def downsample_score_series(
    score_series: dict[str, list[float]],
    *,
    max_points: int,
) -> tuple[dict[str, list[float]], list[int]]:
    if not score_series:
        raise ValueError("score_series must not be empty")

    lengths = {len(values) for values in score_series.values()}
    if len(lengths) != 1:
        raise ValueError("All score series must have the same length")

    total_count = next(iter(lengths))
    indices = select_display_indices(total_count, max_points)
    downsampled = {
        model_key: [values[index] for index in indices]
        for model_key, values in score_series.items()
    }
    one_based_labels = [index + 1 for index in indices]
    return downsampled, one_based_labels


def build_scenario_score_series(
    scenario_results: list[dict[str, object]],
    model_keys: list[str],
) -> tuple[dict[str, list[float]], list[str]]:
    scenario_names: list[str] = []
    scenario_score_series: dict[str, list[float]] = {
        model_key: [] for model_key in model_keys
    }

    for scenario in scenario_results:
        scenario_name = str(scenario["scenario"])
        scenario_names.append(scenario_name)
        ranking = scenario["ranking"]
        assert isinstance(ranking, list)

        scores_for_scenario = {
            str(item["model_key"]): float(item["composite_score"])
            for item in ranking
        }

        for model_key in model_keys:
            if model_key not in scores_for_scenario:
                raise ValueError(
                    f"Scenario '{scenario_name}' missing score for model '{model_key}'"
                )
            scenario_score_series[model_key].append(scores_for_scenario[model_key])

    return scenario_score_series, scenario_names


def _plot_polar_series(
    ax,
    score_series: dict[str, list[float]],
    *,
    design_labels: dict[str, str],
    title: str,
    axis_labels: list[str] | None = None,
    max_ticks: int = 16,
) -> None:
    import numpy as np

    first_series = next(iter(score_series.values()))
    if not first_series:
        raise ValueError("Cannot plot radar sensitivity with empty score series.")

    sample_count = len(first_series)
    theta = np.linspace(0.0, 2 * np.pi, sample_count, endpoint=False)

    all_values = [value for values in score_series.values() for value in values]
    min_result = min(all_values)
    max_result = max(all_values)
    span = max_result - min_result

    if span == 0.0:
        padding = 0.05
        y_min = min_result - padding
        y_max = max_result + padding
    else:
        padding = max(0.02, span * 0.15)
        y_min = min_result - padding
        y_max = max_result + padding

    for model_key, values in score_series.items():
        closed_values = values + [values[0]]
        closed_theta = np.append(theta, 2 * np.pi)
        ax.plot(
            closed_theta,
            closed_values,
            linewidth=2.0,
            label=design_labels.get(model_key, model_key),
        )

    if axis_labels is None:
        axis_labels = [str(index + 1) for index in range(sample_count)]
    if len(axis_labels) != sample_count:
        raise ValueError("axis_labels length must match score series length")

    if sample_count <= max_ticks:
        tick_indices = list(range(sample_count))
    else:
        step = max(1, sample_count // max_ticks)
        tick_indices = list(range(0, sample_count, step))
        if tick_indices[-1] != sample_count - 1:
            tick_indices.append(sample_count - 1)

    ax.set_xticks([theta[index] for index in tick_indices])
    ax.set_xticklabels([axis_labels[index] for index in tick_indices])
    ax.set_ylim(y_min, y_max)
    ax.grid(True, alpha=0.7)
    ax.set_title(title, pad=18)


def plot_radar_sensitivity(
    score_series: dict[str, list[float]],
    *,
    output_path: Path,
    design_labels: dict[str, str],
    title: str = "Sensitivity Analysis",
    axis_labels: list[str] | None = None,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit("matplotlib is required to generate the radar chart.") from exc

    if not score_series:
        raise ValueError("Cannot plot radar sensitivity without score data.")

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(10, 10))
    _plot_polar_series(
        ax,
        score_series,
        design_labels=design_labels,
        title=title,
        axis_labels=axis_labels,
    )
    ax.legend(loc="upper right")
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_primary_radar(
    scenario_score_series: dict[str, list[float]],
    scenario_names: list[str],
    constrained_score_series: dict[str, list[float]],
    constrained_axis_labels: list[str],
    *,
    output_path: Path,
    design_labels: dict[str, str],
    constrained_display_count: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit("matplotlib is required to generate the radar chart.") from exc

    fig, (ax_scenarios, ax_constrained) = plt.subplots(
        1,
        2,
        subplot_kw={"projection": "polar"},
        figsize=(16, 7),
    )

    _plot_polar_series(
        ax_scenarios,
        scenario_score_series,
        design_labels=design_labels,
        title="Primary Named Scenarios",
        axis_labels=scenario_names,
        max_ticks=max(3, len(scenario_names)),
    )
    _plot_polar_series(
        ax_constrained,
        constrained_score_series,
        design_labels=design_labels,
        title=f"Constrained Sensitivity ({constrained_display_count} displayed)",
        axis_labels=constrained_axis_labels,
    )

    handles, labels = ax_scenarios.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.03))
    fig.suptitle("Primary Decision-Support Radar", fontsize=16, weight="bold")
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_supplementary_radar(
    supplementary_score_series: dict[str, list[float]],
    supplementary_axis_labels: list[str],
    *,
    output_path: Path,
    design_labels: dict[str, str],
    supplementary_display_count: int,
) -> None:
    plot_radar_sensitivity(
        supplementary_score_series,
        output_path=output_path,
        design_labels=design_labels,
        title=f"Supplementary Unconstrained Radar ({supplementary_display_count} displayed)",
        axis_labels=supplementary_axis_labels,
    )


def plot_combined_radar(
    scenario_score_series: dict[str, list[float]],
    scenario_names: list[str],
    constrained_score_series: dict[str, list[float]],
    constrained_axis_labels: list[str],
    supplementary_score_series: dict[str, list[float]],
    supplementary_axis_labels: list[str],
    *,
    output_path: Path,
    design_labels: dict[str, str],
    display_count: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit("matplotlib is required to generate the radar chart.") from exc

    fig, (ax_scenarios, ax_primary, ax_supplementary) = plt.subplots(
        1,
        3,
        subplot_kw={"projection": "polar"},
        figsize=(22, 7),
    )

    _plot_polar_series(
        ax_scenarios,
        scenario_score_series,
        design_labels=design_labels,
        title="Primary: Named Scenarios",
        axis_labels=scenario_names,
        max_ticks=max(3, len(scenario_names)),
    )
    _plot_polar_series(
        ax_primary,
        constrained_score_series,
        design_labels=design_labels,
        title=f"Primary: Constrained ({display_count} displayed)",
        axis_labels=constrained_axis_labels,
    )
    _plot_polar_series(
        ax_supplementary,
        supplementary_score_series,
        design_labels=design_labels,
        title=f"Supplementary: Unconstrained ({display_count} displayed)",
        axis_labels=supplementary_axis_labels,
    )

    handles, labels = ax_scenarios.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle(
        "Combined Radar: Primary Decision Basis vs Supplementary Transparency",
        fontsize=16,
        weight="bold",
    )
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def create_run_output_dir(output_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / f"decision_support_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sensitivity analysis for final model selection using five top-level criteria."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        help=(
            "Optional final confirmatory run directory. If omitted, the latest run under "
            "--results-root is used."
        ),
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help=f"Root directory used for run discovery. Default: {DEFAULT_RESULTS_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Directory for timestamped output folders. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--labels-json",
        type=Path,
        help="Optional JSON mapping model_key to display label.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducible sampling. Default: {DEFAULT_SEED}",
    )
    parser.add_argument(
        "--constrained-samples",
        type=int,
        default=DEFAULT_CONSTRAINED_SAMPLES,
        help=(
            "Number of constrained random group-weight samples. "
            f"Default: {DEFAULT_CONSTRAINED_SAMPLES}"
        ),
    )
    parser.add_argument(
        "--unconstrained-samples",
        type=int,
        default=DEFAULT_UNCONSTRAINED_SAMPLES,
        help=(
            "Number of unconstrained random group-weight samples (supplementary). "
            f"Default: {DEFAULT_UNCONSTRAINED_SAMPLES}"
        ),
    )
    parser.add_argument(
        "--plot-sample-count",
        type=int,
        default=DEFAULT_PLOT_SAMPLE_COUNT,
        help=(
            "Maximum number of samples displayed in radar plots for readability. "
            f"Default: {DEFAULT_PLOT_SAMPLE_COUNT}"
        ),
    )
    parser.add_argument(
        "--skip-unconstrained",
        action="store_true",
        help="Skip supplementary unconstrained sampling outputs.",
    )
    parser.add_argument(
        "--security-dominance-margin",
        type=float,
        default=DEFAULT_SECURITY_DOMINANCE_MARGIN,
        help=(
            "Minimum Security minus Efficiency weight gap for constrained sampling. "
            f"Default: {DEFAULT_SECURITY_DOMINANCE_MARGIN}"
        ),
    )
    parser.add_argument(
        "--include-stability-group",
        action="store_true",
        help=(
            "Deprecated no-op: retained for CLI compatibility under the five-criterion design."
        ),
    )
    parser.add_argument(
        "--stability-group-weight",
        type=float,
        default=DEFAULT_STABILITY_GROUP_WEIGHT,
        help=(
            "Deprecated no-op: retained for CLI compatibility under the five-criterion design. "
            f"Default: {DEFAULT_STABILITY_GROUP_WEIGHT}"
        ),
    )
    return parser.parse_args()


def load_design_labels(path: Path | None) -> dict[str, str]:
    if path is None:
        return DEFAULT_DESIGN_LABELS
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()

    if args.include_stability_group:
        print(
            "Note: --include-stability-group is deprecated and ignored under the "
            "five-criterion top-level sensitivity design."
        )

    run_dir = args.run_dir if args.run_dir is not None else find_latest_run_dir(args.results_root)
    design_labels = load_design_labels(args.labels_json)

    decision_data = build_decision_data_from_run(
        run_dir,
        include_stability_group=args.include_stability_group,
    )
    raw_metrics = decision_data["raw_metrics"]
    group_metrics = decision_data["group_metrics"]
    metric_definitions = decision_data["metric_definitions"]
    model_keys = decision_data["model_keys"]
    stability_group_active = False

    within_group_weights = build_within_group_weights(group_metrics)
    normalized_metrics = normalize_metrics(raw_metrics, metric_definitions)
    group_scores = compute_group_scores(
        normalized_metrics,
        group_metrics,
        within_group_weights,
    )

    scenario_group_weights = build_scenario_group_weights(
        group_metrics,
        stability_group_active=stability_group_active,
        stability_group_weight=args.stability_group_weight,
    )
    scenario_results = evaluate_scenarios(
        group_scores,
        scenario_group_weights,
        design_labels,
    )
    scenario_score_series, scenario_names = build_scenario_score_series(
        scenario_results,
        model_keys,
    )

    group_names = list(next(iter(group_scores.values())).keys())

    constrained_samples, constrained_attempts = generate_weight_samples(
        group_names,
        sample_count=args.constrained_samples,
        rng=random.Random(args.seed),
        constrained=True,
        security_margin=args.security_dominance_margin,
    )
    constrained_summary = summarize_weight_sampling(
        group_scores,
        constrained_samples,
        design_labels,
    )
    constrained_score_series = compute_score_series(group_scores, constrained_samples)
    constrained_plot_series, constrained_plot_axis_indices = downsample_score_series(
        constrained_score_series,
        max_points=args.plot_sample_count,
    )
    constrained_plot_axis_labels = [str(index) for index in constrained_plot_axis_indices]
    constrained_summary["sampling"] = {
        "mode": "constrained_primary",
        "seed": args.seed,
        "attempts": constrained_attempts,
        "security_constraints": {
            "security_gt_efficiency": True,
            "security_largest_group": True,
            "security_minus_efficiency_min_margin": args.security_dominance_margin,
        },
        "plot_display_sample_count": len(constrained_plot_axis_labels),
    }

    unconstrained_summary = None
    unconstrained_plot_series = None
    unconstrained_plot_axis_labels = None
    if not args.skip_unconstrained:
        unconstrained_samples, unconstrained_attempts = generate_weight_samples(
            group_names,
            sample_count=args.unconstrained_samples,
            rng=random.Random(args.seed + 1),
            constrained=False,
            security_margin=args.security_dominance_margin,
        )
        unconstrained_summary = summarize_weight_sampling(
            group_scores,
            unconstrained_samples,
            design_labels,
        )
        unconstrained_score_series = compute_score_series(group_scores, unconstrained_samples)
        unconstrained_plot_series, unconstrained_plot_axis_indices = downsample_score_series(
            unconstrained_score_series,
            max_points=args.plot_sample_count,
        )
        unconstrained_plot_axis_labels = [str(index) for index in unconstrained_plot_axis_indices]
        unconstrained_summary["sampling"] = {
            "mode": "unconstrained_supplementary",
            "seed": args.seed + 1,
            "attempts": unconstrained_attempts,
            "plot_display_sample_count": len(unconstrained_plot_axis_labels),
        }

    output_dir = create_run_output_dir(args.output_root)
    primary_dir = output_dir / "primary"
    supplementary_dir = output_dir / "supplementary"
    radar_path = output_dir / "radar.png"
    primary_radar_path = primary_dir / "primary_radar.png"
    supplementary_radar_path = supplementary_dir / "supplementary_radar.png"
    combined_radar_path = output_dir / "combined_radar.png"

    plot_radar_sensitivity(
        constrained_plot_series,
        output_path=radar_path,
        design_labels=design_labels,
        title="Sensitivity Analysis",
        axis_labels=constrained_plot_axis_labels,
    )
    plot_primary_radar(
        scenario_score_series,
        scenario_names,
        constrained_plot_series,
        constrained_plot_axis_labels,
        output_path=primary_radar_path,
        design_labels=design_labels,
        constrained_display_count=len(constrained_plot_axis_labels),
    )
    if unconstrained_plot_series is not None and unconstrained_plot_axis_labels is not None:
        plot_supplementary_radar(
            unconstrained_plot_series,
            unconstrained_plot_axis_labels,
            output_path=supplementary_radar_path,
            design_labels=design_labels,
            supplementary_display_count=len(unconstrained_plot_axis_labels),
        )
        plot_combined_radar(
            scenario_score_series,
            scenario_names,
            constrained_plot_series,
            constrained_plot_axis_labels,
            unconstrained_plot_series,
            unconstrained_plot_axis_labels,
            output_path=combined_radar_path,
            design_labels=design_labels,
            display_count=min(
                len(constrained_plot_axis_labels),
                len(unconstrained_plot_axis_labels),
            ),
        )

    scenario_results_path = primary_dir / "scenario_results.json"
    constrained_path = primary_dir / "constrained_sensitivity.json"
    metrics_snapshot_path = primary_dir / "grouped_metric_snapshot.json"
    summary_path = output_dir / "decision_support_summary.json"
    unconstrained_path = supplementary_dir / "unconstrained_sensitivity.json"

    metrics_snapshot = {
        "model_keys": model_keys,
        "model_labels": {
            model_key: design_labels.get(model_key, model_key) for model_key in model_keys
        },
        "top_level_decision_criteria": list(TOP_LEVEL_DECISION_CRITERIA),
        "secondary_metrics_excluded_from_top_level": list(
            SECONDARY_METRICS_EXCLUDED_FROM_TOP_LEVEL
        ),
        "raw_metrics": raw_metrics,
        "normalized_metrics": normalized_metrics,
        "group_scores": group_scores,
        "group_metrics": group_metrics,
        "within_group_weights": within_group_weights,
        "metric_definitions": metric_definitions,
    }

    summary_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": {
            "run_dir": str(run_dir),
            "benchmark_summary_csv": str(decision_data["benchmark_path"]),
            "evaluation_summary_csv": (
                str(decision_data["evaluation_path"])
                if decision_data["evaluation_path"] is not None
                else None
            ),
            "per_class_summary_csv": (
                str(decision_data["per_class_path"])
                if decision_data["per_class_path"] is not None
                else None
            ),
        },
        "methodology": {
            "primary_method": "scenario_based_scoring_over_top_level_criteria",
            "primary_robustness_check": "constrained_group_weight_sampling",
            "supplementary_method": (
                "unconstrained_group_weight_sampling"
                if unconstrained_summary is not None
                else "not_run"
            ),
            "top_level_criteria_only": True,
            "top_level_decision_criteria": list(TOP_LEVEL_DECISION_CRITERIA),
            "secondary_metrics_excluded_from_top_level": list(
                SECONDARY_METRICS_EXCLUDED_FROM_TOP_LEVEL
            ),
            "security_priority_enforced": True,
            "stability_group_active": stability_group_active,
            "stability_group_cli_compatibility_only": True,
            "plot_display_sample_count": args.plot_sample_count,
        },
        "artifact_paths": {
            "radar_chart_png": str(radar_path),
            "primary_radar_png": str(primary_radar_path),
            "supplementary_radar_png": (
                str(supplementary_radar_path)
                if unconstrained_summary is not None
                else None
            ),
            "combined_radar_png": (
                str(combined_radar_path)
                if unconstrained_summary is not None
                else None
            ),
            "scenario_results_json": str(scenario_results_path),
            "constrained_sensitivity_json": str(constrained_path),
            "grouped_metric_snapshot_json": str(metrics_snapshot_path),
            "decision_support_summary_json": str(summary_path),
            "supplementary_unconstrained_json": (
                str(unconstrained_path) if unconstrained_summary is not None else None
            ),
        },
        "scenario_results": scenario_results,
        "constrained_sensitivity": constrained_summary,
        "supplementary_unconstrained": unconstrained_summary,
    }

    write_json(scenario_results_path, {"scenario_results": scenario_results})
    write_json(constrained_path, constrained_summary)
    write_json(metrics_snapshot_path, metrics_snapshot)
    write_json(summary_path, summary_payload)
    if unconstrained_summary is not None:
        write_json(unconstrained_path, unconstrained_summary)

    print(f"Source run: {run_dir}")

    print("\nTop-level decision criteria (exact set):")
    for metric_name in TOP_LEVEL_DECISION_CRITERIA:
        print(f"- {metric_name}")

    print("\nDecision groups and metrics:")
    for group_name, metrics in group_metrics.items():
        if not metrics:
            continue
        metrics_display = ", ".join(metrics)
        print(f"- {group_name}: {metrics_display}")

    print("\nPrimary scenario winners:")
    for item in scenario_results:
        print(
            f"- {item['scenario']}: {item['winner_model_key']} "
            f"({item['winner_label']})"
        )

    print("\nConstrained winner frequency (primary robustness check):")
    for item in constrained_summary["winner_frequency"]:
        print(
            f"- {item['model_key']}: wins={item['wins']}, "
            f"win_rate={item['win_rate']:.2%}"
        )

    print("\nConstrained rank frequency and average rank:")
    for item in constrained_summary["rank_frequency"]:
        rank_counts = item["rank_counts"]
        rank_counts_display = ", ".join(
            f"R{rank}:{rank_counts[rank]}" for rank in sorted(rank_counts, key=int)
        )
        print(
            f"- {item['model_key']}: avg_rank={item['average_rank']:.4f}; "
            f"{rank_counts_display}"
        )

    if unconstrained_summary is not None:
        print("\nSupplementary unconstrained winner frequency:")
        for item in unconstrained_summary["winner_frequency"]:
            print(
                f"- {item['model_key']}: wins={item['wins']}, "
                f"win_rate={item['win_rate']:.2%}"
            )

    print("\nOutput paths:")
    print(f"- run_folder: {output_dir}")
    print(f"- radar_chart: {radar_path}")
    print(f"- primary/primary_radar: {primary_radar_path}")
    if unconstrained_summary is not None:
        print(f"- supplementary/supplementary_radar: {supplementary_radar_path}")
        print(f"- combined_radar: {combined_radar_path}")
    print(f"- primary/scenario_results: {scenario_results_path}")
    print(f"- primary/constrained_sensitivity: {constrained_path}")
    print(f"- primary/grouped_metric_snapshot: {metrics_snapshot_path}")
    print(f"- summary: {summary_path}")
    if unconstrained_summary is not None:
        print(f"- supplementary/unconstrained_sensitivity: {unconstrained_path}")


if __name__ == "__main__":
    main()

