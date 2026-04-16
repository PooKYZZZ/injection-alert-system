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

METRIC_DIRECTIONS = {
    "Attack-Class Recall": True,
    "Normal False Positive Rate": False,
    "Inference Time": False,
    "Model Size": False,
    "Training Runtime": False,
}

DEFAULT_SEED = 135
DEFAULT_TOTAL_SAMPLES = 4000
DEFAULT_DISPLAY_SAMPLES = 120
DEFAULT_MAX_TICKS = 60


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

    candidates = []
    for candidate in results_root.iterdir():
        if not candidate.is_dir():
            continue
        benchmark_path = candidate / DEFAULT_BENCHMARK_SUMMARY_NAME
        per_class_path = candidate / DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH
        if benchmark_path.exists() and per_class_path.exists():
            candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(
            f"No valid final benchmark runs found under results root: {results_root}"
        )

    # Prefer explicit confirmatory runs when present, while preserving
    # latest-by-mtime selection within the chosen pool.
    confirmatory = [
        candidate for candidate in candidates if "confirmatory" in candidate.name.lower()
    ]
    selection_pool = confirmatory if confirmatory else candidates

    return max(selection_pool, key=lambda candidate: candidate.stat().st_mtime)


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


def build_five_metric_data(run_dir: Path) -> dict[str, object]:
    benchmark_path = run_dir / DEFAULT_BENCHMARK_SUMMARY_NAME
    evaluation_path = run_dir / DEFAULT_EVALUATION_SUMMARY_RELATIVE_PATH
    per_class_path = run_dir / DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH

    benchmark_rows = rows_by_model(load_csv_rows(benchmark_path))
    evaluation_rows = (
        rows_by_model(load_csv_rows(evaluation_path)) if evaluation_path.exists() else {}
    )

    model_keys = infer_model_order(list(benchmark_rows))
    if not model_keys:
        raise ValueError(f"No model rows found in benchmark summary: {benchmark_path}")

    raw_metrics: dict[str, dict[str, float]] = {model_key: {} for model_key in model_keys}
    metric_sources: dict[str, str] = {}

    attack_class_recall = compute_attack_class_recall(per_class_path, model_keys)
    if attack_class_recall is None:
        raise ValueError(
            f"Missing attack-class recall data in {per_class_path}. "
            "This script requires Attack-Class Recall."
        )
    metric_sources[
        "Attack-Class Recall"
    ] = f"{DEFAULT_PER_CLASS_SUMMARY_RELATIVE_PATH}: recall_mean over non-Normal labels"

    normal_fpr = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "normal_false_positive_rate_mean",
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )
    metric_sources["Normal False Positive Rate"] = "normal_false_positive_rate_mean"

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

    inference_time = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        inference_time_field,
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )
    metric_sources["Inference Time"] = inference_time_field

    model_size: dict[str, float] = {}
    for model_key in model_keys:
        model_size[model_key] = parse_required_float(
            benchmark_rows[model_key],
            "model_size_mb_mean",
            source_path=benchmark_path,
        )
    metric_sources["Model Size"] = "model_size_mb_mean"

    training_runtime = extract_metric_values(
        model_keys,
        evaluation_rows,
        benchmark_rows,
        "training_workflow_runtime_sec_mean",
        evaluation_path=evaluation_path if evaluation_path.exists() else None,
        benchmark_path=benchmark_path,
    )
    metric_sources["Training Runtime"] = "training_workflow_runtime_sec_mean"

    for model_key in model_keys:
        raw_metrics[model_key]["Attack-Class Recall"] = attack_class_recall[model_key]
        raw_metrics[model_key]["Normal False Positive Rate"] = normal_fpr[model_key]
        raw_metrics[model_key]["Inference Time"] = inference_time[model_key]
        raw_metrics[model_key]["Model Size"] = model_size[model_key]
        raw_metrics[model_key]["Training Runtime"] = training_runtime[model_key]

    return {
        "model_keys": model_keys,
        "raw_metrics": raw_metrics,
        "metric_sources": metric_sources,
        "benchmark_path": benchmark_path,
        "evaluation_path": evaluation_path if evaluation_path.exists() else None,
        "per_class_path": per_class_path if per_class_path.exists() else None,
    }


def normalize_values(values_by_model: dict[str, float], *, maximize: bool) -> dict[str, float]:
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
) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {model_key: {} for model_key in raw_metrics}

    for metric_name, maximize in METRIC_DIRECTIONS.items():
        metric_values = {
            model_key: metrics[metric_name]
            for model_key, metrics in raw_metrics.items()
        }
        scaled_values = normalize_values(metric_values, maximize=maximize)
        for model_key, scaled in scaled_values.items():
            normalized[model_key][metric_name] = scaled

    return normalized


def sample_weight_vectors(
    metric_names: list[str],
    *,
    sample_count: int,
    rng: random.Random,
) -> list[dict[str, float]]:
    if sample_count <= 0:
        raise ValueError("sample_count must be > 0")

    samples: list[dict[str, float]] = []
    for _ in range(sample_count):
        draws = [rng.gammavariate(1.0, 1.0) for _ in metric_names]
        total = sum(draws)
        samples.append(
            {
                metric_name: draw / total
                for metric_name, draw in zip(metric_names, draws)
            }
        )
    return samples


def rank_models(scores_by_model: dict[str, float]) -> list[str]:
    return sorted(
        scores_by_model,
        key=lambda model_key: (-scores_by_model[model_key], model_key),
    )


def compute_composite_scores(
    normalized_metrics: dict[str, dict[str, float]],
    weights: dict[str, float],
) -> dict[str, float]:
    return {
        model_key: sum(
            metrics[metric_name] * weights[metric_name]
            for metric_name in weights
        )
        for model_key, metrics in normalized_metrics.items()
    }


def run_sensitivity(
    normalized_metrics: dict[str, dict[str, float]],
    weight_samples: list[dict[str, float]],
) -> dict[str, object]:
    model_keys = list(normalized_metrics)
    rank_positions = list(range(1, len(model_keys) + 1))

    winner_counts = {model_key: 0 for model_key in model_keys}
    rank_counts = {
        model_key: {rank: 0 for rank in rank_positions}
        for model_key in model_keys
    }
    rank_sums = {model_key: 0.0 for model_key in model_keys}
    score_series = {model_key: [] for model_key in model_keys}

    for weights in weight_samples:
        scores = compute_composite_scores(normalized_metrics, weights)
        ranked_models = rank_models(scores)
        winner_counts[ranked_models[0]] += 1

        for rank, model_key in enumerate(ranked_models, start=1):
            rank_counts[model_key][rank] += 1
            rank_sums[model_key] += rank

        for model_key, score in scores.items():
            score_series[model_key].append(float(score))

    sample_count = len(weight_samples)

    winner_frequency = [
        {
            "model_key": model_key,
            "wins": int(winner_counts[model_key]),
            "win_rate": float(winner_counts[model_key] / sample_count),
        }
        for model_key in model_keys
    ]
    winner_frequency.sort(key=lambda item: (-int(item["wins"]), str(item["model_key"])))

    average_rank = [
        {
            "model_key": model_key,
            "average_rank": float(rank_sums[model_key] / sample_count),
            "rank_counts": {
                str(rank): int(rank_counts[model_key][rank])
                for rank in rank_positions
            },
            "rank_rates": {
                str(rank): float(rank_counts[model_key][rank] / sample_count)
                for rank in rank_positions
            },
        }
        for model_key in model_keys
    ]
    average_rank.sort(key=lambda item: (float(item["average_rank"]), str(item["model_key"])))

    score_stats = [
        {
            "model_key": model_key,
            "mean_score": float(mean(score_series[model_key])),
            "min_score": float(min(score_series[model_key])),
            "max_score": float(max(score_series[model_key])),
        }
        for model_key in model_keys
    ]
    score_stats.sort(key=lambda item: (-float(item["mean_score"]), str(item["model_key"])))

    return {
        "sample_count": sample_count,
        "score_series": score_series,
        "winner_frequency": winner_frequency,
        "average_rank": average_rank,
        "score_stats": score_stats,
    }


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
) -> tuple[dict[str, list[float]], list[int], list[str]]:
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
    one_based_labels = [str(index + 1) for index in indices]
    return downsampled, indices, one_based_labels


def plot_radar(
    score_series: dict[str, list[float]],
    *,
    output_path: Path,
    design_labels: dict[str, str],
    title: str,
    axis_labels: list[str],
    max_ticks: int,
    show: bool,
) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ModuleNotFoundError as exc:
        raise SystemExit("matplotlib and numpy are required to generate the radar chart.") from exc

    first_series = next(iter(score_series.values()))
    if not first_series:
        raise ValueError("Cannot plot radar chart with empty score series")

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

    if len(axis_labels) != sample_count:
        raise ValueError("axis_labels length must match score series length")

    if sample_count <= max_ticks:
        tick_indices = list(range(sample_count))
    else:
        step = max(1, sample_count // max_ticks)
        tick_indices = list(range(0, sample_count, step))
        if tick_indices[-1] != sample_count - 1:
            tick_indices.append(sample_count - 1)

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(11, 11))

    for model_key, values in score_series.items():
        closed_values = values + [values[0]]
        closed_theta = np.append(theta, 2 * np.pi)
        ax.plot(
            closed_theta,
            closed_values,
            linewidth=2.0,
            label=design_labels.get(model_key, model_key),
        )

    ax.set_xticks([theta[index] for index in tick_indices])
    ax.set_xticklabels([axis_labels[index] for index in tick_indices])
    ax.set_ylim(y_min, y_max)
    ax.grid(True, alpha=0.7)
    ax.set_title(title, pad=18)
    ax.legend(loc="upper right")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


def create_run_output_dir(output_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / f"five_metric_sensitivity_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Direct five-metric (no-grouping) sensitivity analysis for final model selection."
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
        "--sample-count",
        "--samples",
        dest="sample_count",
        type=int,
        default=DEFAULT_TOTAL_SAMPLES,
        help=(
            "Total number of sampled five-metric weight vectors. "
            f"Default: {DEFAULT_TOTAL_SAMPLES}"
        ),
    )
    parser.add_argument(
        "--plot-sample-count",
        "--display-samples",
        dest="plot_sample_count",
        type=int,
        default=DEFAULT_DISPLAY_SAMPLES,
        help=(
            "Number of sampled cases shown on the radar chart. "
            f"Default: {DEFAULT_DISPLAY_SAMPLES}"
        ),
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=(
            "Maximum angular tick labels shown on the radar chart. "
            f"Default: {DEFAULT_MAX_TICKS}"
        ),
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the saved radar figure interactively.",
    )
    return parser.parse_args()


def load_design_labels(path: Path | None) -> dict[str, str]:
    if path is None:
        return DEFAULT_DESIGN_LABELS
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()

    run_dir = args.run_dir if args.run_dir is not None else find_latest_run_dir(args.results_root)
    design_labels = load_design_labels(args.labels_json)
    timestamp_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )

    data = build_five_metric_data(run_dir)
    raw_metrics = data["raw_metrics"]
    model_keys = data["model_keys"]
    normalized_metrics = normalize_metrics(raw_metrics)

    metric_names = list(METRIC_DIRECTIONS)
    weight_samples = sample_weight_vectors(
        metric_names,
        sample_count=args.sample_count,
        rng=random.Random(args.seed),
    )

    sensitivity = run_sensitivity(normalized_metrics, weight_samples)
    score_series = sensitivity["score_series"]

    display_score_series, display_indices, display_axis_labels = downsample_score_series(
        score_series,
        max_points=args.plot_sample_count,
    )

    output_dir = create_run_output_dir(args.output_root)
    radar_path = output_dir / "five_metric_radar.png"
    summary_path = output_dir / "five_metric_sensitivity_summary.json"
    snapshot_path = output_dir / "five_metric_metric_snapshot.json"

    plot_radar(
        display_score_series,
        output_path=radar_path,
        design_labels=design_labels,
        title="Five-Metric Direct Sensitivity Analysis (No Grouping)",
        axis_labels=display_axis_labels,
        max_ticks=args.max_ticks,
        show=args.show,
    )

    snapshot_payload = {
        "model_keys": model_keys,
        "model_labels": {
            model_key: design_labels.get(model_key, model_key) for model_key in model_keys
        },
        "metrics_used": metric_names,
        "metric_directions": {
            metric_name: ("maximize" if maximize else "minimize")
            for metric_name, maximize in METRIC_DIRECTIONS.items()
        },
        "metric_source_mapping": data["metric_sources"],
        "metric_sources": data["metric_sources"],
        "raw_metrics": raw_metrics,
        "normalized_metrics": normalized_metrics,
    }

    summary_payload = {
        "timestamp": timestamp_utc,
        "timestamp_utc": timestamp_utc,
        "source": {
            "run_dir": str(run_dir),
            "benchmark_summary_csv": str(data["benchmark_path"]),
            "evaluation_summary_csv": (
                str(data["evaluation_path"]) if data["evaluation_path"] is not None else None
            ),
            "per_class_summary_csv": (
                str(data["per_class_path"]) if data["per_class_path"] is not None else None
            ),
        },
        "methodology": {
            "mode": "direct_five_metric_no_grouping",
            "metrics_used": metric_names,
            "metric_directions": {
                metric_name: ("maximize" if maximize else "minimize")
                for metric_name, maximize in METRIC_DIRECTIONS.items()
            },
            "seed": args.seed,
            "total_internal_samples": args.sample_count,
            "displayed_sample_count": len(display_axis_labels),
            "total_samples": args.sample_count,
            "display_samples": len(display_axis_labels),
            "display_case_indices_zero_based": display_indices,
            "display_case_indices_one_based": [index + 1 for index in display_indices],
        },
        "output_paths": {
            "run_folder": str(output_dir),
            "radar_png": str(radar_path),
            "summary_json": str(summary_path),
            "metric_snapshot_json": str(snapshot_path),
        },
        "artifacts": {
            "run_folder": str(output_dir),
            "radar_png": str(radar_path),
            "summary_json": str(summary_path),
            "metric_snapshot_json": str(snapshot_path),
        },
        "winner_frequency": sensitivity["winner_frequency"],
        "average_rank": sensitivity["average_rank"],
        "score_stats": sensitivity["score_stats"],
    }

    write_json(snapshot_path, snapshot_payload)
    write_json(summary_path, summary_payload)

    print(f"Source run: {run_dir}")
    print("\nMetrics used (exact five):")
    for metric_name, maximize in METRIC_DIRECTIONS.items():
        direction = "maximize" if maximize else "minimize"
        print(f"- {metric_name} ({direction})")

    print("\nWinner frequency:")
    for item in sensitivity["winner_frequency"]:
        print(
            f"- {item['model_key']}: wins={item['wins']}, "
            f"win_rate={item['win_rate']:.2%}"
        )

    print("\nAverage rank:")
    for item in sensitivity["average_rank"]:
        print(
            f"- {item['model_key']}: avg_rank={item['average_rank']:.4f}"
        )

    print("\nOutput paths:")
    print(f"- run_folder: {output_dir}")
    print(f"- radar_png: {radar_path}")
    print(f"- summary_json: {summary_path}")
    print(f"- metric_snapshot_json: {snapshot_path}")


if __name__ == "__main__":
    main()
