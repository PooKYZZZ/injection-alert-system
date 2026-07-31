from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from waf_runtime.render import render_candidate


def _item(index: int) -> dict[str, object]:
    return {
        "entry_id": index + 1,
        "recommendation_id": index + 1,
        "source_ip": f"198.51.100.{(index % 254) + 1}",
        "request_path": "/records/search",
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=15)
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


def run_capacity_measurements(
    output: Path,
    *,
    repetitions: int = 5,
    levels: tuple[int, ...] = (0, 1, 64),
) -> dict[str, object]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    if any(level < 0 or level > 64 for level in levels):
        raise ValueError("capacity levels must be between 0 and 64")

    measurements: list[dict[str, object]] = []
    for level in levels:
        samples: list[float] = []
        sizes: list[int] = []
        items = [_item(index) for index in range(level)]
        for _ in range(repetitions):
            started = time.perf_counter()
            candidate = render_candidate(level + 1, items)
            samples.append(round((time.perf_counter() - started) * 1000, 3))
            sizes.append(len(candidate.content.encode("ascii")))
        ordered = sorted(samples)
        measurements.append(
            {
                "entries": level,
                "samples": len(samples),
                "min_ms": min(samples),
                "median_ms": round(statistics.median(samples), 3),
                "max_ms": max(samples),
                "p95_ms": ordered[
                    min(len(ordered) - 1, max(0, round(0.95 * len(ordered)) - 1))
                ],
                "candidate_bytes": sizes[0],
            }
        )

    result = {
        "schema_version": 1,
        "measurement": "pr7_candidate_render_capacity",
        "scope": "local_disposable_contract_measurement",
        "repetitions": repetitions,
        "levels": measurements,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    run_capacity_measurements(args.output, repetitions=args.repetitions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
