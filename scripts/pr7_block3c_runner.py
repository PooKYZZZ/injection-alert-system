"""Run bounded local PR7 3C checks through the existing pytest harness."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from scripts.pr7_block3_evidence import utc_now, validate_id, write_json

ROOT = Path(__file__).resolve().parents[1]
FOCUSED = [
    "tests/e2e/test_pr7_block3c_harness.py",
    "tests/e2e/test_pr7_block3_measurements.py",
    "tests/waf_runtime",
]


def run_3c(run_id: str, *, disposable: bool = False) -> dict[str, Any]:
    validate_id(run_id, label="run ID")
    command = [sys.executable, "-m", "pytest", "-q", "--tb=short", *FOCUSED]
    if disposable:
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "tests/e2e/test_pr7_block3.py",
        ]
    env = os.environ.copy()
    env["NOTIFICATION_WORKER_ENABLED"] = "false"
    env["NOTIFICATION_WORKER_REQUIRED"] = "false"
    if disposable:
        env["PR7_RUN_BLOCK3_E2E"] = "1"
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=900 if disposable else 180,
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "command": command,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "return_code": result.returncode,
        "output_tail": (result.stdout + result.stderr)[-8000:],
        "cleanup": "delegated to existing disposable harness" if disposable else "not required",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--disposable", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_3c(args.run_id, disposable=args.disposable)
    write_json(args.output, result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
