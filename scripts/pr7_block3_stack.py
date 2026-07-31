"""Safely start and stop disposable PR7 Block 3 Compose profiles."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from scripts.pr7_block3_evidence import validate_id

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_3B = (
    "docker-compose.yml",
    "docker-compose.demo-target.yml",
    "docker-compose.target-cloudflare.yml",
    "docker-compose.pr7-block3b.yml",
)
COMPOSE_3C = (
    "docker-compose.yml",
    "docker-compose.pr7-block3.yml",
    "docker-compose.pr7-block3c.yml",
)


def compose_command(profile: str, run_id: str, action: str) -> list[str]:
    if profile not in {"3b", "3c"}:
        raise ValueError("profile must be 3b or 3c")
    if action not in {"start", "stop"}:
        raise ValueError("action must be start or stop")
    validate_id(run_id, label="run ID")
    files = COMPOSE_3B if profile == "3b" else COMPOSE_3C
    command = ["docker", "compose", "--project-name", f"pr7-{run_id}"]
    for compose_file in files:
        command.extend(("-f", compose_file))
    command.extend(("--profile", "demo-target" if profile == "3b" else "pr7-block3"))
    if profile == "3b":
        command.extend(("--profile", "target-cloudflare"))
    command.extend(
        [
            "up" if action == "start" else "down",
            "-d" if action == "start" else "--volumes",
            "--remove-orphans",
        ]
    )
    if action == "start":
        command.extend(("--build", "--wait", "--wait-timeout", "300"))
    return command


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("start", "stop"))
    parser.add_argument("--profile", choices=("3b", "3c"), required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = subprocess.run(
        compose_command(args.profile, args.run_id, args.action),
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
