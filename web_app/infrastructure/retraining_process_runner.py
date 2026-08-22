"""Restricted subprocess adapter for the detached local retraining worker."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

WORKER_MODULE = "ml_model.retraining.dashboard_worker"
_SAFE_ENV_KEYS = frozenset(
    {"PATH", "PYTHONPATH", "IAS_PROJECT_ROOT", "PYTHONNOUSERSITE", "SYSTEMROOT"}
)


@dataclass(frozen=True, slots=True)
class WorkerProcessHandle:
    pid: int
    started_at: datetime


class RetrainingProcessError(RuntimeError):
    """Raised when the detached worker cannot be started safely."""


def build_restricted_worker_environment(
    *,
    project_root: Path | str | None = None,
    extra_safe_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the allowlisted environment used by every retraining child."""

    extra = dict(extra_safe_environment or {})
    if any(key not in _SAFE_ENV_KEYS for key in extra):
        raise ValueError("worker environment contains an unallowlisted key")

    environment = {
        key: value for key, value in os.environ.items() if key in _SAFE_ENV_KEYS
    }
    environment["PYTHONNOUSERSITE"] = "1"
    if project_root is not None:
        environment["IAS_PROJECT_ROOT"] = str(
            Path(project_root).expanduser().resolve()
        )
    environment.update(extra)
    return environment


class RetrainingProcessRunner:
    """Start only the repository's allowlisted worker module."""

    def __init__(
        self,
        *,
        python_executable: Path | str | None = None,
        project_root: Path | str | None = None,
        smoke: bool = True,
        timeout_seconds: int = 3600,
        extra_safe_environment: Mapping[str, str] | None = None,
    ) -> None:
        self.python_executable = Path(python_executable or sys.executable).expanduser()
        if not self.python_executable.is_absolute():
            raise ValueError("worker Python executable must be absolute")
        self.project_root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else Path.cwd().resolve()
        )
        if not self.project_root.is_dir():
            raise ValueError("worker project root does not exist")
        if timeout_seconds <= 0:
            raise ValueError("worker timeout must be positive")
        self._smoke = bool(smoke)
        self._timeout_seconds = int(timeout_seconds)
        self._extra_safe_environment = dict(extra_safe_environment or {})
        build_restricted_worker_environment(
            extra_safe_environment=self._extra_safe_environment
        )

    def build_command(self, root: Path | str) -> list[str]:
        configured_root = Path(root).expanduser().resolve()
        command = [
            str(self.python_executable),
            "-m",
            WORKER_MODULE,
            "--root",
            str(configured_root),
            "--max-runtime-seconds",
            str(self._timeout_seconds),
            "--timeout-seconds",
            str(self._timeout_seconds),
        ]
        if self._smoke:
            command.append("--smoke")
        return command

    def _safe_environment(self) -> dict[str, str]:
        return build_restricted_worker_environment(
            project_root=self.project_root,
            extra_safe_environment=self._extra_safe_environment,
        )

    def start_worker(self, root: Path | str) -> WorkerProcessHandle:
        arguments = self.build_command(root)
        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        try:
            process = subprocess.Popen(
                arguments,
                cwd=str(self.project_root),
                env=self._safe_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=creation_flags,
                start_new_session=os.name != "nt",
            )
        except (OSError, ValueError) as exc:
            raise RetrainingProcessError(
                "local worker process could not be started"
            ) from exc
        return WorkerProcessHandle(
            pid=int(process.pid),
            started_at=datetime.now(timezone.utc),
        )


__all__ = [
    "build_restricted_worker_environment",
    "RetrainingProcessError",
    "RetrainingProcessRunner",
    "WorkerProcessHandle",
]
