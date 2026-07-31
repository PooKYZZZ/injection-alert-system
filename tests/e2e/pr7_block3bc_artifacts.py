from __future__ import annotations

import json
import platform
import statistics
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TimingSeries:
    name: str
    samples_ms: list[float] = field(default_factory=list)

    def add(self, value_ms: float) -> None:
        if value_ms < 0:
            raise ValueError("timing values cannot be negative")
        self.samples_ms.append(round(value_ms, 3))

    def summary(self) -> dict[str, Any]:
        if not self.samples_ms:
            return {"name": self.name, "samples": 0}
        values = sorted(self.samples_ms)
        percentile = values[min(len(values) - 1, max(0, round(0.95 * len(values)) - 1))]
        return {
            "name": self.name,
            "samples": len(values),
            "min_ms": values[0],
            "median_ms": round(statistics.median(values), 3),
            "max_ms": values[-1],
            "p95_ms": percentile,
        }


def _version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    line = (result.stdout or result.stderr).splitlines()
    return line[0][:200] if line else None


def build_run_metadata(
    *,
    run_id: str,
    cybertrace_commit: str,
    portal_commit: str,
    model_version: str,
    model_hashes: dict[str, str],
    image_digests: dict[str, str],
    commands: list[dict[str, Any]],
    timings: list[TimingSeries],
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in run_id):
        raise ValueError("run_id must be bounded and correlation-safe")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
            "docker": _version(["docker", "--version"]),
        },
        "commits": {
            "cybertrace": cybertrace_commit,
            "portal": portal_commit,
        },
        "model": {
            "version": model_version,
            "sha256": dict(model_hashes),
        },
        "images": dict(image_digests),
        "commands": commands,
        "timings": [timing.summary() for timing in timings],
        "cleanup": cleanup,
    }


def write_run_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
