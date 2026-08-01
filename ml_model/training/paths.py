"""Portable project and training-artifact paths."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT_ENV = "IAS_PROJECT_ROOT"
TRAINING_OUTPUT_ENV = "IAS_TRAINING_OUTPUT_DIR"


def _is_project_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / "ml_model").is_dir()


def resolve_project_root(explicit: Path | str | None = None) -> Path:
    """Resolve the repository root without depending on the launch directory."""

    configured = explicit if explicit is not None else os.environ.get(PROJECT_ROOT_ENV)
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if not _is_project_root(candidate):
            raise FileNotFoundError(
                f"Project root is invalid: {candidate}. "
                "Expected pyproject.toml and ml_model/."
            )
        return candidate

    module_path = Path(__file__).resolve()
    for candidate in (module_path.parent, *module_path.parents):
        if _is_project_root(candidate):
            return candidate

    raise FileNotFoundError(
        "Could not find the repository root. Set IAS_PROJECT_ROOT or run "
        "from an installed package."
    )


def resolve_configured_path(
    value: Path | str | None, *, project_root: Path
) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def default_data_dir(dataset_version: str, *, project_root: Path) -> Path:
    return project_root / "data" / "processed" / dataset_version


def default_training_output_dir(*, project_root: Path) -> Path:
    configured = resolve_configured_path(
        os.environ.get(TRAINING_OUTPUT_ENV), project_root=project_root
    )
    return configured or (project_root / "ml_model" / "results" / "benchmarks")
