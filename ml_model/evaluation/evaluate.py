"""Validate and summarize completed ML experiment bundles.

This module intentionally does not promote or deploy a model. It provides the
script-first validation boundary used before a later promotion decision.
"""

from __future__ import annotations

import argparse
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
    report = validate_run_bundle(args.run_dir)
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
