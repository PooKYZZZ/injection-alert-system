from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(relative_path: Path | str) -> Path:
    candidate = Path(relative_path).expanduser()
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("project path must be repository-relative")
    return (PROJECT_ROOT / candidate).resolve()


__all__ = ["PROJECT_ROOT", "project_path"]
