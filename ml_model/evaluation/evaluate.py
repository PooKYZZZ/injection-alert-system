"""Validate and summarize completed ML experiment bundles.

This module intentionally does not promote or deploy a model. It provides the
script-first validation boundary used before a later promotion decision.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "run_manifest.json",
    "run_status.json",
    "run_progress.json",
    "run_failures.json",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_run_bundle(run_dir: Path) -> dict[str, Any]:
    """Return a deterministic completeness report for one experiment run."""

    run_path = Path(run_dir).expanduser().resolve()
    missing = [name for name in REQUIRED_FILES if not (run_path / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Run bundle '{run_path}' is missing required files: {', '.join(missing)}"
        )

    manifest = _load_json(run_path / "run_manifest.json")
    status = _load_json(run_path / "run_status.json")
    progress = _load_json(run_path / "run_progress.json")
    failures = _load_json(run_path / "run_failures.json")

    model_keys = manifest.get("model_keys", [])
    completed_models = manifest.get("completed_model_keys", [])
    failures_are_empty = isinstance(failures, list) and not failures
    is_complete = (
        status.get("state") == "aggregation_completed"
        and isinstance(model_keys, list)
        and isinstance(completed_models, list)
        and sorted(model_keys) == sorted(completed_models)
        and failures_are_empty
    )

    return {
        "status": "complete" if is_complete else "incomplete",
        "run_dir": str(run_path),
        "run_name": manifest.get("run_name"),
        "dataset_version": manifest.get("dataset_version"),
        "model_keys": model_keys,
        "completed_models": completed_models,
        "run_state": status.get("state"),
        "completed_models_count": progress.get("completed_models"),
        "total_models_count": progress.get("total_models"),
        "failure_count": len(failures) if isinstance(failures, list) else None,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_seed_summaries(run_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(Path(run_dir).glob("**/summary_metrics.json")):
        payload = _load_json(path)
        if isinstance(payload, dict):
            rows.append({**payload, "summary_path": str(path)})
    return rows


def evaluate_run_bundle(run_dir: Path) -> dict[str, Any]:
    """Validate a run and materialize script-first evaluation summary artifacts."""

    report = validate_run_bundle(run_dir)
    run_path = Path(run_dir).expanduser().resolve()
    evaluation_dir = run_path / "evaluation"
    seed_summaries = _load_seed_summaries(run_path)
    _write_csv(evaluation_dir / "evaluation_seed_summary.csv", seed_summaries)
    report = {
        **report,
        "evaluation_dir": str(evaluation_dir),
        "seed_summary_count": len(seed_summaries),
        "generated_files": [
            "evaluation/evaluation_seed_summary.csv",
            "evaluation/evaluation_summary.json",
        ],
    }
    (evaluation_dir / "evaluation_summary.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--write-report",
        type=Path,
        help="Optional path for the JSON validation report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    report = evaluate_run_bundle(args.run_dir)
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
