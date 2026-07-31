"""Bounded preflight for PR7 Block 3 proof runs."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts.pr7_block3_evidence import utc_now, validate_id, write_json

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_3B_FILES = (
    "docker-compose.yml",
    "docker-compose.demo-target.yml",
    "docker-compose.target-cloudflare.yml",
    "docker-compose.pr7-block3b.yml",
)
REQUIRED_3C_FILES = (
    "docker-compose.yml",
    "docker-compose.pr7-block3.yml",
    "docker-compose.pr7-block3c.yml",
)


def _run(command: list[str], *, timeout: float = 15) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return result.returncode, (result.stdout or result.stderr).strip()[-1000:]


def run_preflight(profile: str, run_id: str) -> dict[str, Any]:
    validate_id(run_id, label="run ID")
    required = REQUIRED_3B_FILES if profile == "3b" else REQUIRED_3C_FILES
    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "name": "python",
            "status": "PASS",
            "detail": os.sys.version.split()[0],
        }
    )
    for executable in ("docker", "docker-compose"):
        if shutil.which(executable):
            checks.append({"name": executable, "status": "PASS"})
        elif executable == "docker-compose" and shutil.which("docker"):
            checks.append(
                {
                    "name": executable,
                    "status": "PASS",
                    "detail": "docker compose plugin is used",
                }
            )
        else:
            checks.append({"name": executable, "status": "FAIL"})

    missing = [name for name in required if not (ROOT / name).is_file()]
    checks.append(
        {
            "name": "compose_files",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }
    )

    if shutil.which("docker"):
        code, detail = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
        checks.append(
            {
                "name": "docker_daemon",
                "status": "PASS" if code == 0 else "FAIL",
                "detail": detail,
            }
        )

    token_path = Path(os.environ.get("CLOUDFLARED_TARGET_TOKEN_FILE", ""))
    if profile == "3b":
        checks.append(
            {
                "name": "cloudflare_token_file",
                "status": "PASS"
                if token_path.is_file() and token_path.stat().st_size > 0
                else "NOT_RUN",
                "detail": "presence checked; value never read",
            }
        )

    return {
        "schema_version": 1,
        "run_id": run_id,
        "profile": profile,
        "generated_at_utc": utc_now(),
        "checks": checks,
        "overall": (
            "FAIL"
            if any(check["status"] == "FAIL" for check in checks)
            else "PASS"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("3b", "3c"), required=True)
    parser.add_argument("--run-id", default="pr7-preflight")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(args.output, run_preflight(args.profile, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
