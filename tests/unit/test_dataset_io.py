from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ml_model.preprocessing.dataset_io import load_dataset_file_manifest


def _write_dataset_manifest(root: Path, *, files: dict[str, bytes]) -> None:
    entries: list[str] = []
    for name, content in files.items():
        (root / name).write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        entries.append(f"{digest}  {name}")
    (root / "checksums.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")


def test_dataset_manifest_verifies_the_declared_files(tmp_path: Path):
    _write_dataset_manifest(
        tmp_path,
        files={
            "train.parquet": b"train",
            "validation.parquet": b"validation",
            "test.parquet": b"test",
        },
    )

    manifest = load_dataset_file_manifest(tmp_path)

    assert set(manifest["files"]) == {"train.parquet", "validation.parquet", "test.parquet"}


def test_dataset_manifest_rejects_a_missing_declared_file(tmp_path: Path):
    _write_dataset_manifest(
        tmp_path,
        files={
            "train.parquet": b"train",
            "validation.parquet": b"validation",
            "test.parquet": b"test",
        },
    )
    (tmp_path / "test.parquet").unlink()

    with pytest.raises(ValueError, match="missing dataset file"):
        load_dataset_file_manifest(tmp_path)


def test_dataset_manifest_rejects_modified_file_contents(tmp_path: Path):
    _write_dataset_manifest(
        tmp_path,
        files={
            "train.parquet": b"train",
            "validation.parquet": b"validation",
            "test.parquet": b"test",
        },
    )
    (tmp_path / "test.parquet").write_bytes(b"modified")

    with pytest.raises(ValueError, match="checksum mismatch"):
        load_dataset_file_manifest(tmp_path)


def test_dataset_manifest_rejects_duplicate_entries(tmp_path: Path):
    content = b"train"
    digest = hashlib.sha256(content).hexdigest()
    _write_dataset_manifest(
        tmp_path,
        files={
            "train.parquet": content,
            "validation.parquet": b"validation",
            "test.parquet": b"test",
        },
    )
    checksums = (tmp_path / "checksums.txt").read_text(encoding="utf-8")
    (tmp_path / "checksums.txt").write_text(
        checksums + f"{digest}  train.parquet\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_dataset_file_manifest(tmp_path)
