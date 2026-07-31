"""Create a final bounded PR7 Block 3 report from safe evidence artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.pr7_block3_evidence import read_json, utc_now, write_json


def finalize(preflight: Path, coordinator: Path | None, output: Path) -> None:
    preflight_result = read_json(preflight)
    coordinator_result = read_json(coordinator) if coordinator else None
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "preflight": preflight_result,
        "external_sources": coordinator_result,
        "hosted_or_production_ready": False,
        "status": (
            coordinator_result.get("overall", "NOT_RUN")
            if coordinator_result
            else "NOT_RUN"
        ),
        "limitations": [
            "Final packaging is not authorization to enable production enforcement.",
            "Missing external source or server-side correlation remains NOT_RUN.",
        ],
    }
    write_json(output, report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--coordinator", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    finalize(args.preflight, args.coordinator, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
