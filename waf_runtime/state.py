from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on Windows hosts
    fcntl = None

CANONICAL_EMPTY_CONTENT = b"# PR7 dynamic WAF candidate\n"


class CandidateStateStore:
    """Persistent, same-filesystem state for one local WAF instance."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.candidates_dir = self.root / "candidates"
        self.lock_path = self.root / "activation.lock"
        self.metadata_path = self.root / "selected.json"
        self.selected_path = self.root / "selected.conf"
        self.previous_path = self.root / "previous.conf"
        self.canonical_empty_path = self.root / "empty.conf"
        self.disabled_path = self.root / "DISABLED"
        self.root.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)
        self._ensure_canonical_empty()
        if not self.selected_path.exists():
            self._atomic_write(
                self.selected_path, self.canonical_empty_path.read_bytes()
            )
        if not self.metadata_path.exists():
            self.write_metadata(self._empty_metadata("mode_empty"))

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self.lock_path.open("a+b") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def lock_inode(self) -> int:
        return self.lock_path.stat().st_ino

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    def write_candidate(self, name: str, content: bytes) -> Path:
        if (
            not name.startswith("candidate-")
            or not name.endswith(".conf")
            or Path(name).name != name
        ):
            raise ValueError("invalid candidate name")
        path = self.candidates_dir / name
        if path.exists():
            if path.read_bytes() == content:
                return path
            raise FileExistsError(name)
        self._atomic_write(path, content)
        return path

    def read_candidate(self, name: str) -> bytes:
        path = {
            "selected.conf": self.selected_path,
            "previous.conf": self.previous_path,
            "empty.conf": self.canonical_empty_path,
        }.get(name)
        if path is None:
            if (
                Path(name).name != name
                or not name.startswith("candidate-")
                or not name.endswith(".conf")
            ):
                raise ValueError("invalid candidate name")
            path = self.candidates_dir / name
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(name)
        return path.read_bytes()

    def select_candidate(
        self, candidate: Path, expected_checksum: str | None = None
    ) -> None:
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError("candidate must be a regular file")
        content = candidate.read_bytes()
        if (
            expected_checksum is not None
            and self.checksum(content) != expected_checksum
        ):
            raise ValueError("candidate changed after validation")
        if self.selected_path.exists():
            self._atomic_write(self.previous_path, self.selected_path.read_bytes())
        self._atomic_write(self.selected_path, content)

    def restore_previous(self) -> None:
        if self.previous_path.is_symlink() or not self.previous_path.is_file():
            raise FileNotFoundError("previous candidate is unavailable")
        self._atomic_write(self.selected_path, self.previous_path.read_bytes())

    def selected_checksum_matches(self, expected: str | None) -> bool:
        return (
            isinstance(expected, str)
            and self.selected_path.is_file()
            and not self.selected_path.is_symlink()
            and self.checksum(self.selected_path.read_bytes()) == expected
        )

    def empty_state_matches(self, kind: str) -> bool:
        if kind not in {"mode_empty", "disabled_empty", "pending_empty"}:
            return False
        metadata = self.read_metadata()
        if (
            metadata.get("selected_kind") != kind
            or not metadata.get("selected_at")
            or metadata.get("selected_source_revision") is not None
            or metadata.get("selected_source_state_checksum_sha256") is not None
            or not self.selected_checksum_matches(
                metadata.get("selected_file_checksum_sha256")
            )
        ):
            return False
        try:
            return self.selected_path.read_bytes() == CANONICAL_EMPTY_CONTENT
        except OSError:
            return False

    def set_empty_state(self, kind: str) -> None:
        if kind not in {"mode_empty", "disabled_empty", "pending_empty"}:
            raise ValueError("invalid empty state kind")
        self.select_candidate(self.canonical_empty_path)
        self.write_metadata(self.empty_metadata(kind))

    def write_metadata(self, metadata: dict) -> None:
        self._atomic_write(
            self.metadata_path,
            (json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n").encode(
                "ascii"
            ),
        )

    def read_metadata(self) -> dict:
        try:
            value = json.loads(self.metadata_path.read_text(encoding="ascii"))
        except (OSError, ValueError):
            value = self._empty_metadata("pending_empty")
            self.write_metadata(value)
        if not isinstance(value, dict):
            value = self._empty_metadata("pending_empty")
            self.write_metadata(value)
        return value

    def set_disabled(self, disabled: bool) -> None:
        if disabled:
            self._atomic_write(self.disabled_path, b"disabled\n")
        elif self.disabled_path.exists():
            self.disabled_path.unlink()

    def is_disabled(self) -> bool:
        return self.disabled_path.is_file()

    def prune_candidates(self, keep: int = 1) -> None:
        candidates = sorted(
            self.candidates_dir.glob("candidate-*.conf"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in candidates[keep:]:
            path.unlink(missing_ok=True)

    @staticmethod
    def checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def empty_metadata(self, kind: str) -> dict:
        return {
            "metadata_schema_version": 1,
            "selected_kind": kind,
            "selected_source_revision": None,
            "selected_source_state_checksum_sha256": None,
            "selected_file_checksum_sha256": self.checksum(CANONICAL_EMPTY_CONTENT),
            "selected_at": None,
        }

    def _ensure_canonical_empty(self) -> None:
        if (
            self.canonical_empty_path.is_symlink()
            or not self.canonical_empty_path.is_file()
            or self.canonical_empty_path.read_bytes() != CANONICAL_EMPTY_CONTENT
        ):
            self._atomic_write(self.canonical_empty_path, CANONICAL_EMPTY_CONTENT)

    _empty_metadata = empty_metadata
