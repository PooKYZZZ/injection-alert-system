"""Deterministic JSON and Markdown reports for the retraining simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_simulation_report(output_dir: Path | str, payload: Mapping[str, Any]) -> Path:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / "simulation_report.json"
    report_path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def render_simulation_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Controlled 20-Day Retraining Simulation",
        "",
        "This report describes a controlled offline simulation using prepared "
        "daily batches.",
        "",
        f"- Experiment: `{payload.get('experiment', {}).get('name', 'unknown')}`",
        f"- Version: `{payload.get('experiment', {}).get('version', 'unknown')}`",
        f"- Final status: `{payload.get('status', 'UNKNOWN')}`",
        f"- Baseline status: `{payload.get('baseline_status', 'UNKNOWN')}`",
        "- Execution mode: `{}".format(
            payload.get("experiment", {}).get("execution_mode", "UNKNOWN")
        )
        + "`",
        "- Real native training: `{}".format(
            payload.get("experiment", {}).get("real_training_status", "UNKNOWN")
        )
        + "`",
        "- Model-quality conclusion: `{}".format(
            payload.get("experiment", {}).get("model_quality_conclusion", "UNKNOWN")
        )
        + "`",
        "",
        "## Daily results",
        "",
        "| Day | Status | Stage | Input hash | Snapshot hash | Error |",
        "|---:|---|---|---|---|---|",
    ]
    for day in payload.get("days", []):
        lines.append(
            (
                "| {day} | {status} | {stage} | `{input_hash}` | "
                "`{snapshot_hash}` | {error} |"
            ).format(
                day=day.get("day", ""),
                status=day.get("status", ""),
                stage=day.get("stage", ""),
                input_hash=day.get("input_hash", ""),
                snapshot_hash=day.get("snapshot_hash", ""),
                error=str(day.get("error", "")).replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Execution boundary",
            "",
            "Smoke mode validates orchestration, hashing, snapshot creation, "
            "gate wiring, and failure handling only; it does not run native "
            "training and cannot support a model-quality conclusion.",
            "Full baseline, one-seed, three-seed, and 20-day native training "
            "remain laptop operations unless fresh artifacts and reports are "
            "present.",
            "",
        ]
    )
    return "\n".join(lines)


def write_simulation_markdown(
    output_dir: Path | str, payload: Mapping[str, Any]
) -> Path:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / "simulation_report.md"
    report_path.write_text(render_simulation_markdown(payload), encoding="utf-8")
    return report_path
