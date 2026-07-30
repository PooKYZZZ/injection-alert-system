from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "docs/project-ops/pr7-block3-artifact-lock.json"


def load_artifact_lock() -> dict[str, Any]:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model_lock(run_dir: Path) -> dict[str, Any]:
    lock = load_artifact_lock()
    for relative_path, expected_hash in lock["model"]["files"].items():
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


def require_pinned_compose_images(compose_path: Path) -> None:
    lock = load_artifact_lock()
    compose = compose_path.read_text(encoding="utf-8")
    waf_dockerfile = compose_path.parent / "Dockerfile.pr7-waf"
    if waf_dockerfile.is_file():
        compose += waf_dockerfile.read_text(encoding="utf-8")
    for image in lock["containers"].values():
        if image not in compose:
            raise AssertionError(f"compose image is not pinned to lock: {image}")
