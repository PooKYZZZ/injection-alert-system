from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RESULTS_ROOT = (
    REPO_ROOT
    / "ml_model"
    / "notebooks"
    / "training done"
    / "Final training"
    / "results"
)
DEFAULT_OUTPUT_ROOT = Path("artifacts") / "sensitivity_analysis_runs"

OPTION_1_SUBDIR = "option_1_security_gate"
OPTION_2_SUBDIR = "option_2_grouped_weighting"
OPTION_3_SUBDIR = "option_3_direct_five_metric"

OPTION_1_NAME = "Security gate + post-screen ranking"
OPTION_2_NAME = "Grouped / hierarchical weighting"
OPTION_3_NAME = "Direct five-metric no-grouping sensitivity"

POST_SCREEN_WEIGHTS = {
    "Attack-Class Recall": 0.40,
    "Normal False Positive Rate": 0.35,
    "Inference Time": 0.15,
    "Model Size": 0.05,
    "Training Runtime": 0.05,
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def create_method_comparison_dir(output_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / f"method_comparison_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def find_latest_valid_confirmatory_run(results_root: Path) -> Path:
    if not results_root.exists():
        raise FileNotFoundError(f"Results root does not exist: {results_root}")

    candidates: list[Path] = []
    for candidate in results_root.iterdir():
        if not candidate.is_dir():
            continue

        benchmark = candidate / "model_benchmark_summary.csv"
        evaluation = candidate / "evaluation" / "final_model_comparison.csv"
        per_class = candidate / "evaluation" / "aggregated_per_class_summary.csv"

        if benchmark.exists() and evaluation.exists() and per_class.exists():
            candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(
            f"No valid final result runs found under: {results_root}"
        )

    confirmatory = [
        candidate for candidate in candidates if "confirmatory" in candidate.name.lower()
    ]
    pool = confirmatory if confirmatory else candidates
    return max(pool, key=lambda item: item.stat().st_mtime)


def find_latest_child_dir(parent: Path, prefix: str) -> Path:
    candidates = [
        child
        for child in parent.iterdir()
        if child.is_dir() and child.name.startswith(prefix)
    ]
    if not candidates:
        raise FileNotFoundError(f"No child directory starting with '{prefix}' in {parent}")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def load_five_metric_module() -> ModuleType:
    module_path = SCRIPT_DIR / "sensitivity_analysis_five_metrics.py"
    spec = importlib.util.spec_from_file_location(
        "sensitivity_analysis_five_metrics_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plot_security_gate_ranking(ranking: list[dict[str, object]], output_path: Path) -> Path | None:
    if not ranking:
        return None

    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return None

    labels = [str(item["label"]) for item in ranking]
    scores = [float(item["post_screen_score"]) for item in ranking]

    fig, ax = plt.subplots(figsize=(10, 5))
    positions = list(range(len(labels)))
    ax.bar(positions, scores, color="#1f77b4")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Post-screen composite score")
    ax.set_title("Option 1 Security Gate: Post-screen Ranking")
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def run_option_1_security_gate(
    *,
    run_dir: Path,
    output_dir: Path,
    min_attack_class_recall: float,
    max_normal_false_positive_rate: float,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    five_metric_module = load_five_metric_module()
    data = five_metric_module.build_five_metric_data(run_dir)
    raw_metrics = data["raw_metrics"]
    normalized_metrics = five_metric_module.normalize_metrics(raw_metrics)
    model_keys = data["model_keys"]

    design_labels = getattr(five_metric_module, "DEFAULT_DESIGN_LABELS", {})
    metric_directions = getattr(five_metric_module, "METRIC_DIRECTIONS", {})

    gate_results: list[dict[str, object]] = []
    passed_models: list[str] = []
    failed_models: list[str] = []

    for model_key in model_keys:
        attack_class_recall = float(raw_metrics[model_key]["Attack-Class Recall"])
        normal_false_positive_rate = float(raw_metrics[model_key]["Normal False Positive Rate"])

        attack_recall_pass = attack_class_recall >= min_attack_class_recall
        normal_fpr_pass = normal_false_positive_rate <= max_normal_false_positive_rate
        passed = attack_recall_pass and normal_fpr_pass

        if passed:
            passed_models.append(model_key)
        else:
            failed_models.append(model_key)

        gate_results.append(
            {
                "model_key": model_key,
                "label": design_labels.get(model_key, model_key),
                "attack_class_recall": attack_class_recall,
                "normal_false_positive_rate": normal_false_positive_rate,
                "attack_recall_pass": attack_recall_pass,
                "normal_fpr_pass": normal_fpr_pass,
                "passed_gate": passed,
            }
        )

    if passed_models:
        ranking_pool = passed_models
        ranking_pool_note = "Only gate-passing models are ranked."
    else:
        ranking_pool = list(model_keys)
        ranking_pool_note = (
            "No models passed the gate. Ranking fell back to all shortlisted models."
        )

    score_by_model = {
        model_key: sum(
            float(normalized_metrics[model_key][metric_name]) * weight
            for metric_name, weight in POST_SCREEN_WEIGHTS.items()
        )
        for model_key in ranking_pool
    }

    ranked_model_keys = sorted(
        ranking_pool,
        key=lambda model_key: (-score_by_model[model_key], model_key),
    )

    ranking: list[dict[str, object]] = []
    for rank, model_key in enumerate(ranked_model_keys, start=1):
        ranking.append(
            {
                "rank": rank,
                "model_key": model_key,
                "label": design_labels.get(model_key, model_key),
                "post_screen_score": float(score_by_model[model_key]),
                "raw_metrics": {
                    metric_name: float(raw_metrics[model_key][metric_name])
                    for metric_name in POST_SCREEN_WEIGHTS
                },
            }
        )

    winner_key = ranking[0]["model_key"] if ranking else None
    winner_label = (
        design_labels.get(str(winner_key), str(winner_key)) if winner_key is not None else None
    )

    metric_snapshot_path = output_dir / "option_1_metric_snapshot.json"
    method_summary_path = output_dir / "method_summary.json"
    ranking_plot_path = output_dir / "option_1_post_screen_ranking.png"

    ranking_plot_written = plot_security_gate_ranking(ranking, ranking_plot_path)

    snapshot_payload = {
        "method": "security_gate_post_screen_ranking",
        "model_keys": model_keys,
        "model_labels": {
            model_key: design_labels.get(model_key, model_key) for model_key in model_keys
        },
        "metrics_used": list(metric_directions.keys()),
        "metric_directions": {
            metric_name: ("maximize" if bool(maximize) else "minimize")
            for metric_name, maximize in metric_directions.items()
        },
        "metric_source_mapping": data["metric_sources"],
        "raw_metrics": raw_metrics,
        "normalized_metrics": normalized_metrics,
        "gate_results": gate_results,
    }

    method_summary_payload = {
        "timestamp": now_utc_iso(),
        "method": {
            "name": OPTION_1_NAME,
            "id": OPTION_1_SUBDIR,
            "mode": "security_gate_then_post_screen_ranking",
            "description": (
                "Apply a strict security gate first, then rank only passing models using "
                "a weighted post-screen composite score."
            ),
        },
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
        "gate": {
            "rule_id": "attack_recall_and_normal_fpr_threshold",
            "rule_description": (
                "Pass if Attack-Class Recall >= min_attack_class_recall and "
                "Normal False Positive Rate <= max_normal_false_positive_rate."
            ),
            "thresholds": {
                "min_attack_class_recall": min_attack_class_recall,
                "max_normal_false_positive_rate": max_normal_false_positive_rate,
            },
            "all_models_passed": len(passed_models) == len(model_keys),
            "passed_models": passed_models,
            "failed_models": failed_models,
            "gate_results": gate_results,
        },
        "post_screen_ranking": {
            "ranking_pool": ranking_pool,
            "ranking_pool_note": ranking_pool_note,
            "weights": POST_SCREEN_WEIGHTS,
            "winner_model_key": winner_key,
            "winner_label": winner_label,
            "ranking": ranking,
        },
        "artifacts": {
            "method_summary_json": str(method_summary_path),
            "metric_snapshot_json": str(metric_snapshot_path),
            "ranking_plot_png": str(ranking_plot_written) if ranking_plot_written is not None else None,
        },
    }

    write_json(metric_snapshot_path, snapshot_payload)
    write_json(method_summary_path, method_summary_payload)

    return {
        "method_id": OPTION_1_SUBDIR,
        "method_name": OPTION_1_NAME,
        "winner": winner_key,
        "ranking": [item["model_key"] for item in ranking],
        "subfolder": str(output_dir),
        "method_summary_json": str(method_summary_path),
        "explanation": (
            "Security-first gate applied before ranking. Models that fail the gate are excluded "
            "from post-screen ranking unless none pass."
        ),
    }


def run_cli_script(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def run_option_2_grouped_weighting(
    *,
    run_dir: Path,
    output_dir: Path,
    seed: int,
    constrained_samples: int,
    unconstrained_samples: int,
    plot_sample_count: int,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped_script = SCRIPT_DIR / "sensitivity_analysis.py"
    command = [
        sys.executable,
        str(grouped_script),
        "--run-dir",
        str(run_dir),
        "--output-root",
        str(output_dir),
        "--seed",
        str(seed),
        "--constrained-samples",
        str(constrained_samples),
        "--unconstrained-samples",
        str(unconstrained_samples),
        "--plot-sample-count",
        str(plot_sample_count),
    ]
    run_cli_script(command)

    grouped_run_dir = find_latest_child_dir(output_dir, "decision_support_")
    grouped_summary_path = grouped_run_dir / "decision_support_summary.json"
    grouped_summary = read_json(grouped_summary_path)

    winner_frequency = grouped_summary["constrained_sensitivity"]["winner_frequency"]
    average_rank = grouped_summary["constrained_sensitivity"]["average_rank"]

    winner_key = winner_frequency[0]["model_key"] if winner_frequency else None
    ranking = [row["model_key"] for row in average_rank]

    method_summary_path = output_dir / "method_summary.json"
    method_summary_payload = {
        "timestamp": now_utc_iso(),
        "method": {
            "name": OPTION_2_NAME,
            "id": OPTION_2_SUBDIR,
            "mode": "grouped_hierarchical_weighting",
            "description": (
                "Grouped decision-support methodology using top-level Security and Efficiency "
                "group weighting with constrained sensitivity outputs."
            ),
        },
        "source": {
            "run_dir": str(run_dir),
            "grouped_summary_json": str(grouped_summary_path),
            "grouped_run_output_dir": str(grouped_run_dir),
        },
        "winner": {
            "model_key": winner_key,
            "basis": "constrained_sensitivity.winner_frequency",
        },
        "ranking": {
            "model_keys": ranking,
            "basis": "constrained_sensitivity.average_rank",
        },
        "artifacts": {
            "grouped_summary_json": str(grouped_summary_path),
            "grouped_metric_snapshot_json": str(grouped_run_dir / "primary" / "grouped_metric_snapshot.json"),
            "primary_radar_png": str(grouped_run_dir / "primary" / "primary_radar.png"),
            "method_summary_json": str(method_summary_path),
        },
    }
    write_json(method_summary_path, method_summary_payload)

    return {
        "method_id": OPTION_2_SUBDIR,
        "method_name": OPTION_2_NAME,
        "winner": winner_key,
        "ranking": ranking,
        "subfolder": str(output_dir),
        "method_summary_json": str(method_summary_path),
        "explanation": (
            "Uses grouped/hierarchical weighting over Security and Efficiency with constrained "
            "sensitivity as the primary robustness lens."
        ),
    }


def run_option_3_direct_five_metric(
    *,
    run_dir: Path,
    output_dir: Path,
    seed: int,
    sample_count: int,
    plot_sample_count: int,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    direct_script = SCRIPT_DIR / "sensitivity_analysis_five_metrics.py"
    command = [
        sys.executable,
        str(direct_script),
        "--run-dir",
        str(run_dir),
        "--output-root",
        str(output_dir),
        "--seed",
        str(seed),
        "--sample-count",
        str(sample_count),
        "--plot-sample-count",
        str(plot_sample_count),
    ]
    run_cli_script(command)

    direct_run_dir = find_latest_child_dir(output_dir, "five_metric_sensitivity_")
    direct_summary_path = direct_run_dir / "five_metric_sensitivity_summary.json"
    direct_summary = read_json(direct_summary_path)

    winner_frequency = direct_summary["winner_frequency"]
    average_rank = direct_summary["average_rank"]

    winner_key = winner_frequency[0]["model_key"] if winner_frequency else None
    ranking = [row["model_key"] for row in average_rank]

    method_summary_path = output_dir / "method_summary.json"
    method_summary_payload = {
        "timestamp": now_utc_iso(),
        "method": {
            "name": OPTION_3_NAME,
            "id": OPTION_3_SUBDIR,
            "mode": "direct_five_metric_no_grouping",
            "description": (
                "Direct five-metric sensitivity over Attack-Class Recall, Normal FPR, "
                "Inference Time, Model Size, and Training Runtime with no grouping."
            ),
        },
        "source": {
            "run_dir": str(run_dir),
            "direct_summary_json": str(direct_summary_path),
            "direct_run_output_dir": str(direct_run_dir),
        },
        "winner": {
            "model_key": winner_key,
            "basis": "winner_frequency",
        },
        "ranking": {
            "model_keys": ranking,
            "basis": "average_rank",
        },
        "artifacts": {
            "direct_summary_json": str(direct_summary_path),
            "direct_metric_snapshot_json": str(direct_run_dir / "five_metric_metric_snapshot.json"),
            "direct_radar_png": str(direct_run_dir / "five_metric_radar.png"),
            "method_summary_json": str(method_summary_path),
        },
    }
    write_json(method_summary_path, method_summary_payload)

    return {
        "method_id": OPTION_3_SUBDIR,
        "method_name": OPTION_3_NAME,
        "winner": winner_key,
        "ranking": ranking,
        "subfolder": str(output_dir),
        "method_summary_json": str(method_summary_path),
        "explanation": (
            "No-grouping direct weighting/sensitivity over exactly five explicit metrics."
        ),
    }


def write_parent_level_outputs(
    *,
    parent_dir: Path,
    run_dir: Path,
    option_1_result: dict[str, object],
    option_2_result: dict[str, object],
    option_3_result: dict[str, object],
) -> tuple[Path, Path]:
    combined_summary_path = parent_dir / "combined_method_comparison_summary.json"
    comparison_table_path = parent_dir / "method_comparison_table.json"

    methods = [option_1_result, option_2_result, option_3_result]

    combined_summary_payload = {
        "timestamp": now_utc_iso(),
        "source_run_path": str(run_dir),
        "method_names": [
            OPTION_1_NAME,
            OPTION_2_NAME,
            OPTION_3_NAME,
        ],
        "method_subfolders": {
            OPTION_1_SUBDIR: str(parent_dir / OPTION_1_SUBDIR),
            OPTION_2_SUBDIR: str(parent_dir / OPTION_2_SUBDIR),
            OPTION_3_SUBDIR: str(parent_dir / OPTION_3_SUBDIR),
        },
        "methods": methods,
        "notes": {
            "intentional_difference": (
                "These methods are intentionally different in structure and assumptions; "
                "different winners can be expected."
            ),
            "comparison_scope": (
                "Method 1 uses security gate filtering first, Method 2 uses grouped hierarchical "
                "weighting, and Method 3 uses direct five-metric no-grouping sensitivity."
            ),
        },
    }

    comparison_table_payload = {
        "timestamp": combined_summary_payload["timestamp"],
        "source_run_path": str(run_dir),
        "winner_by_method": {
            method["method_name"]: method["winner"] for method in methods
        },
        "ranking_by_method": {
            method["method_name"]: method["ranking"] for method in methods
        },
    }

    write_json(combined_summary_path, combined_summary_payload)
    write_json(comparison_table_path, comparison_table_payload)
    return combined_summary_path, comparison_table_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run three distinct model-selection methodologies side by side and write "
            "a combined comparison output."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        help=(
            "Optional final run directory. If omitted, the latest valid confirmatory run "
            "under --results-root is used."
        ),
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help=f"Root directory for run auto-discovery. Default: {DEFAULT_RESULTS_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Root directory for method comparison outputs. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=135,
        help="Random seed passed to stochastic methods. Default: 135",
    )
    parser.add_argument(
        "--min-attack-class-recall",
        type=float,
        default=0.995,
        help="Method 1 gate threshold: minimum Attack-Class Recall. Default: 0.995",
    )
    parser.add_argument(
        "--max-normal-fpr",
        type=float,
        default=0.005,
        help="Method 1 gate threshold: maximum Normal False Positive Rate. Default: 0.005",
    )
    parser.add_argument(
        "--grouped-constrained-samples",
        type=int,
        default=4000,
        help="Method 2 constrained sample count. Default: 4000",
    )
    parser.add_argument(
        "--grouped-unconstrained-samples",
        type=int,
        default=4000,
        help="Method 2 unconstrained sample count. Default: 4000",
    )
    parser.add_argument(
        "--grouped-plot-sample-count",
        type=int,
        default=150,
        help="Method 2 radar display sample count. Default: 150",
    )
    parser.add_argument(
        "--direct-sample-count",
        type=int,
        default=4000,
        help="Method 3 direct sample count. Default: 4000",
    )
    parser.add_argument(
        "--direct-plot-sample-count",
        type=int,
        default=120,
        help="Method 3 radar display sample count. Default: 120",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_dir = args.run_dir if args.run_dir is not None else find_latest_valid_confirmatory_run(args.results_root)

    parent_dir = create_method_comparison_dir(args.output_root)
    option_1_dir = parent_dir / OPTION_1_SUBDIR
    option_2_dir = parent_dir / OPTION_2_SUBDIR
    option_3_dir = parent_dir / OPTION_3_SUBDIR

    option_1_result = run_option_1_security_gate(
        run_dir=run_dir,
        output_dir=option_1_dir,
        min_attack_class_recall=args.min_attack_class_recall,
        max_normal_false_positive_rate=args.max_normal_fpr,
    )

    option_2_result = run_option_2_grouped_weighting(
        run_dir=run_dir,
        output_dir=option_2_dir,
        seed=args.seed,
        constrained_samples=args.grouped_constrained_samples,
        unconstrained_samples=args.grouped_unconstrained_samples,
        plot_sample_count=args.grouped_plot_sample_count,
    )

    option_3_result = run_option_3_direct_five_metric(
        run_dir=run_dir,
        output_dir=option_3_dir,
        seed=args.seed,
        sample_count=args.direct_sample_count,
        plot_sample_count=args.direct_plot_sample_count,
    )

    combined_summary_path, comparison_table_path = write_parent_level_outputs(
        parent_dir=parent_dir,
        run_dir=run_dir,
        option_1_result=option_1_result,
        option_2_result=option_2_result,
        option_3_result=option_3_result,
    )

    print(f"Source run: {run_dir}")
    print(f"Parent output: {parent_dir}")
    print("\nMethod winners:")
    print(f"- {OPTION_1_NAME}: {option_1_result['winner']}")
    print(f"- {OPTION_2_NAME}: {option_2_result['winner']}")
    print(f"- {OPTION_3_NAME}: {option_3_result['winner']}")
    print("\nOutput paths:")
    print(f"- {OPTION_1_SUBDIR}: {option_1_dir}")
    print(f"- {OPTION_2_SUBDIR}: {option_2_dir}")
    print(f"- {OPTION_3_SUBDIR}: {option_3_dir}")
    print(f"- combined_summary_json: {combined_summary_path}")
    print(f"- comparison_table_json: {comparison_table_path}")


if __name__ == "__main__":
    main()
