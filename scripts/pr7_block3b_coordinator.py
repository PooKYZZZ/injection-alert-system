"""Correlate two source-agent bundles without inventing server-side evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.pr7_block3_evidence import read_json, validate_id, utc_now, write_json


def _by_scenario(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["scenario"]: item["result"] for item in bundle.get("results", [])}


def coordinate(run_id: str, source_paths: list[Path]) -> dict[str, Any]:
    validate_id(run_id, label="run ID")
    bundles = [read_json(path) for path in source_paths]
    if len(bundles) < 2:
        raise ValueError("at least two source bundles are required")
    if any(bundle.get("run_id") != run_id for bundle in bundles):
        raise ValueError("source bundle run IDs do not match")
    labels = [str(bundle.get("source_label", "")) for bundle in bundles]
    if len(set(labels)) != len(labels):
        raise ValueError("source labels must be distinct")

    source_results: list[dict[str, Any]] = []
    for bundle in bundles:
        cases = _by_scenario(bundle)
        checks = {
            "normal": cases.get("normal", {}).get("status_code") in {200, 204},
            "static_crs": cases.get("static_crs", {}).get("status_code") == 403,
            "forged_headers": cases.get("forged_headers", {}).get("status_code")
            != 200,
        }
        source_results.append(
            {
                "source_label": bundle["source_label"],
                "checks": {
                    name: ("PASS" if passed else "INCONCLUSIVE")
                    for name, passed in checks.items()
                },
            }
        )
    all_pass = all(
        status == "PASS"
        for source in source_results
        for status in source["checks"].values()
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "source_labels": labels,
        "checks": source_results,
        "overall": "PASS" if all_pass else "INCONCLUSIVE",
        "limitations": [
            "Server-side WAF, bridge, model, revision, and sentinel correlation must be joined separately.",
            "This report does not assert hosted or production readiness.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(args.output, coordinate(args.run_id, args.source))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
