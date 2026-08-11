"""Deterministic content identities for local retraining inputs and artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ml_model.retraining.dashboard_contracts import canonical_json


class ContentDigestError(ValueError):
    """A content tree cannot be safely hashed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ContentDigestError("content file is unreadable") from exc
    return digest.hexdigest()


def compute_content_digest(root_path: Path | str) -> str:
    """Hash every regular file and relative name in deterministic order."""

    raw_root = Path(root_path).expanduser()
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise ContentDigestError("content root is not a directory")
    try:
        root = raw_root.resolve()
        entries: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_symlink():
                raise ContentDigestError("content tree contains a symbolic link")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ContentDigestError("content tree contains an unsafe entry")
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    except (OSError, ValueError) as exc:
        if isinstance(exc, ContentDigestError):
            raise
        raise ContentDigestError("content tree is unreadable") from exc
    if not entries:
        raise ContentDigestError("content tree is empty")
    return hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


__all__ = ["ContentDigestError", "compute_content_digest", "sha256_file"]
