from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from collections.abc import Sequence
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "docs/project-ops/pr7-block3-artifact-lock.json"


def load_artifact_lock(lock_path: Path = LOCK_PATH) -> dict[str, Any]:
    if not lock_path.is_file():
        raise AssertionError(f"artifact lock is missing: {lock_path}")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssertionError(f"artifact lock is unreadable: {lock_path}") from exc
    if not isinstance(lock, dict) or lock.get("schema_version") != 2:
        raise AssertionError(f"unsupported artifact lock: {lock_path}")
    return lock


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model_lock(run_dir: Path, lock_path: Path = LOCK_PATH) -> dict[str, Any]:
    lock = load_artifact_lock(lock_path)
    for locked_file in lock["model"]["files"]:
        relative_path = locked_file["path"]
        expected_hash = locked_file["sha256"]
        artifact = run_dir / relative_path
        if not artifact.is_file():
            raise AssertionError(f"required model artifact is missing: {artifact}")
        actual_hash = sha256(artifact)
        if actual_hash != expected_hash:
            raise AssertionError(
                f"artifact checksum mismatch for {relative_path}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
    return lock


def require_portal_commit(portal_path: Path, expected_sha: str) -> None:
    actual = subprocess.run(
        ["git", "-C", str(portal_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != expected_sha:
        raise AssertionError(
            f"portal commit mismatch: expected {expected_sha}, got {actual}"
        )

    status = subprocess.run(
        ["git", "-C", str(portal_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise AssertionError(f"portal checkout is not clean: {portal_path}")


def require_pinned_compose_images(
    compose_paths: Path | Sequence[Path],
    lock_path: Path = LOCK_PATH,
) -> None:
    lock = load_artifact_lock(lock_path)
    paths = [compose_paths] if isinstance(compose_paths, Path) else list(compose_paths)
    compose = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    waf_dockerfile = paths[0].parent / "Dockerfile.pr7-waf"
    if waf_dockerfile.is_file():
        compose += waf_dockerfile.read_text(encoding="utf-8")
    for image in lock["containers"].values():
        if image not in compose:
            raise AssertionError(f"compose image is not pinned to lock: {image}")
