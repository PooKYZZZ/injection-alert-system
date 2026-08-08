"""Synthetic memory and comparison benchmark for the retraining index."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import time
import tracemalloc
from typing import Any

import pandas as pd

from ml_model.retraining.snapshots import ContaminationIndex


def _synthetic_text(index: int) -> str:
    digest = hashlib.sha256(f"synthetic-{index}".encode("utf-8")).hexdigest()
    body_length = 64 + (index % 128)
    return f"GET /synthetic/{index:08d}/" + (digest * 8)[:body_length]


def run_benchmark(*, row_count: int = 100_000, query_count: int = 10) -> dict[str, Any]:
    """Build a representative synthetic index and report memory/comparison data."""

    if row_count < 1 or query_count < 1:
        raise ValueError("row_count and query_count must be positive")
    tracemalloc.start()
    build_started = time.perf_counter()
    rows = [
        {"combined_payload": _synthetic_text(index), "final_label": "Normal"}
        for index in range(row_count)
    ]
    frames = [("train", pd.DataFrame(rows))]
    index = ContaminationIndex.from_historical_frames(frames)
    build_seconds = time.perf_counter() - build_started
    del frames, rows
    gc.collect()

    queries = [
        {
            "sample_id": f"benchmark-query-{index_number}",
            "model_input_text": _synthetic_text(row_count + index_number),
            "ground_truth_label": "Normal",
        }
        for index_number in range(query_count)
    ]
    query_started = time.perf_counter()
    report = index.check_new_samples(queries)
    query_seconds = time.perf_counter() - query_started
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "historical_row_count": index.historical_row_count,
        "query_count": query_count,
        "build_seconds": round(build_seconds, 6),
        "query_seconds": round(query_seconds, 6),
        "peak_memory_mib": round(peak_bytes / (1024 * 1024), 3),
        "retained_memory_mib": round(current_bytes / (1024 * 1024), 3),
        "candidate_comparisons_checked": report["candidate_comparisons_checked"],
        "full_scan_comparisons": row_count * query_count,
        "candidate_comparison_ratio": round(
            report["candidate_comparisons_checked"] / (row_count * query_count),
            6,
        ),
        "exact_overlap_count": report["exact_overlap_count"],
        "near_duplicate_count": report["near_duplicate_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--queries", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run_benchmark(row_count=args.rows, query_count=args.queries)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
