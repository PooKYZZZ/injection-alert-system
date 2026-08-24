"""Fail-closed local staging promotion and rollback for approved candidates."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Mapping

from ml_model.preprocessing.model_input import (
    MODEL_INPUT_HASH_POLICY,
    validate_supported_model_input_version,
)
from ml_model.retraining.content_digest import (
    ContentDigestError,
    compute_content_digest,
    sha256_file,
)
from ml_model.retraining.dashboard_contracts import (
    CANONICAL_LABELS,
    get_run_artifact_directory,
    is_valid_run_id,
)

CANDIDATE_ARTIFACT_DIR_NAME = "candidate_model"
ACTIVE_MODEL_POINTER_FILENAME = "active_model.json"
MODEL_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_ARTIFACT_FILES = frozenset(
    {"serving_manifest.json", "config.json", "tokenizer_config.json"}
)
MODEL_WEIGHT_FILES = frozenset({"model.safetensors", "pytorch_model.bin"})
TOKENIZER_FILES = frozenset(
    {
        "tokenizer.json",
        "vocab.txt",
        "merges.txt",
        "spiece.model",
        "sentencepiece.bpe.model",
    }
)
ALLOWED_ARTIFACT_FILES = frozenset(
    {
        *REQUIRED_ARTIFACT_FILES,
        *MODEL_WEIGHT_FILES,
        *TOKENIZER_FILES,
        "added_tokens.json",
        "special_tokens_map.json",
        "generation_config.json",
        "config_used.json",
        "eval_report.json",
        "summary_metrics.json",
        "per_class_metrics.json",
        "calibration.json",
        "git_hash.txt",
        "provenance.json",
        "MODEL_CARD.md",
        "best_distilbert_ckpt.pt",
    }
)


class StagingDeploymentError(RuntimeError):
    """Bounded local staging failure with no raw artifact or loader output."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        rolled_back: bool = False,
    ) -> None:
        if not re.fullmatch(r"[A-Z0-9_]{1,64}", code):
            raise ValueError("staging error code is not bounded")
        self.code = code
        self.safe_message = message.replace("\r", " ").replace("\n", " ")[:240]
        self.rolled_back = rolled_back
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class StagingPreflight:
    run_id: str
    candidate_path: Path
    candidate_model_version: str
    candidate_model_digest: str
    preprocessing_version: str


@dataclass(frozen=True, slots=True)
class StagingDeploymentRecord:
    run_id: str
    candidate_model_version: str
    candidate_model_digest: str
    previous_staging_version: str
    previous_staging_digest: str
    previous_staging_dir_name: str
    archive_name: str
    active_model_version: str
    active_model_digest: str
    preprocessing_version: str
    status: str = "PREPARED"

    def to_payload(self) -> dict[str, str]:
        return {
            "artifact_version": "staging-deployment.v1",
            "run_id": self.run_id,
            "candidate_model_version": self.candidate_model_version,
            "candidate_model_digest": self.candidate_model_digest,
            "previous_staging_version": self.previous_staging_version,
            "previous_staging_digest": self.previous_staging_digest,
            "previous_staging_dir_name": self.previous_staging_dir_name,
            "archive_name": self.archive_name,
            "active_model_version": self.active_model_version,
            "active_model_digest": self.active_model_digest,
            "preprocessing_version": self.preprocessing_version,
            "status": self.status,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "StagingDeploymentRecord":
        if payload.get("artifact_version") != "staging-deployment.v1":
            raise StagingDeploymentError(
                "DEPLOYMENT_RECORD_INVALID",
                "deployment record version is invalid",
            )
        required = (
            "run_id",
            "candidate_model_version",
            "candidate_model_digest",
            "previous_staging_version",
            "previous_staging_digest",
            "previous_staging_dir_name",
            "archive_name",
            "active_model_version",
            "active_model_digest",
            "preprocessing_version",
        )
        if any(not isinstance(payload.get(key), str) for key in required):
            raise StagingDeploymentError(
                "DEPLOYMENT_RECORD_INVALID",
                "deployment record is incomplete",
            )
        values = {key: str(payload[key]) for key in required}
        if not is_valid_run_id(values["run_id"]):
            raise StagingDeploymentError(
                "DEPLOYMENT_RECORD_INVALID", "deployment run identity is invalid"
            )
        for value, name in (
            (values["candidate_model_digest"], "candidate model digest"),
            (values["previous_staging_digest"], "previous staging digest"),
            (values["active_model_digest"], "active model digest"),
        ):
            if not DIGEST_PATTERN.fullmatch(value):
                raise StagingDeploymentError(
                    "DEPLOYMENT_RECORD_INVALID",
                    f"{name} is invalid",
                )
        for value, name in (
            (values["candidate_model_version"], "candidate model version"),
            (values["previous_staging_version"], "previous staging version"),
            (values["previous_staging_dir_name"], "previous staging directory"),
            (values["archive_name"], "archive name"),
            (values["active_model_version"], "active model version"),
        ):
            if (
                not value
                or len(value) > 240
                or any(character in value for character in ("/", "\\", ".."))
            ):
                raise StagingDeploymentError(
                    "DEPLOYMENT_RECORD_INVALID",
                    f"{name} is invalid",
                )
        try:
            validate_supported_model_input_version(
                values["preprocessing_version"], context="deployment record"
            )
        except ValueError as exc:
            raise StagingDeploymentError(
                "DEPLOYMENT_RECORD_INVALID",
                "deployment preprocessing metadata is invalid",
            ) from exc
        status = payload.get("status", "PREPARED")
        if not isinstance(status, str) or status not in {
            "PREPARED",
            "DEPLOYED",
            "ROLLED_BACK",
        }:
            raise StagingDeploymentError(
                "DEPLOYMENT_RECORD_INVALID",
                "deployment status is invalid",
            )
        return cls(**values, status=status)


@dataclass(frozen=True, slots=True)
class ActiveStagingPointer:
    model_version: str
    artifact_digest: str
    directory: str
    preprocessing_version: str


@dataclass(frozen=True, slots=True)
class StagingDeploymentPlan:
    preflight: StagingPreflight
    previous_staging_path: Path
    previous_staging_version: str
    previous_staging_digest: str
    previous_staging_dir_name: str
    archive_name: str
    target_path: Path
    record: StagingDeploymentRecord


LoadValidator = Callable[[Path, str], Any]


def compute_artifact_digest(artifact_path: Path) -> str:
    try:
        return compute_content_digest(artifact_path)
    except ContentDigestError as exc:
        raise StagingDeploymentError(
            "CANDIDATE_ARTIFACT_INVALID", "candidate artifact cannot be verified"
        ) from exc


def _read_json(path: Path, *, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StagingDeploymentError(code, "staging metadata is unreadable") from exc
    if not isinstance(payload, dict):
        raise StagingDeploymentError(code, "staging metadata must be an object")
    return payload


class LocalStagingAdapter:
    """Promote only validated run-local artifacts into the controlled staging tree."""

    def __init__(
        self,
        *,
        staging_root: Path | str,
        archive_root: Path | str,
        load_validator: LoadValidator | None = None,
        reload_callback: LoadValidator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.staging_root = Path(staging_root).expanduser().resolve()
        self.archive_root = Path(archive_root).expanduser().resolve()
        self._validate_roots()
        self._load_validator = load_validator or self._default_load_validator
        self._reload_callback = reload_callback or self._load_validator
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _validate_roots(self) -> None:
        for root in (self.staging_root, self.archive_root):
            if any(part.lower() == "production" for part in root.parts):
                raise ValueError("local staging adapter cannot target production")
        if self.staging_root.name.lower() != "staging":
            raise ValueError("local staging root must end in staging")
        if self.staging_root == self.archive_root:
            raise ValueError("staging and archive roots must differ")
        if (
            self.staging_root in self.archive_root.parents
            or self.archive_root in self.staging_root.parents
        ):
            raise ValueError("staging and archive roots must not contain one another")

    @staticmethod
    def _validate_version(value: str, field_name: str) -> None:
        if not isinstance(value, str) or MODEL_VERSION_PATTERN.fullmatch(value) is None:
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", f"{field_name} is invalid"
            )

    @staticmethod
    def _validate_digest(value: str, field_name: str) -> None:
        if not isinstance(value, str) or DIGEST_PATTERN.fullmatch(value) is None:
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", f"{field_name} is invalid"
            )

    @property
    def active_pointer_path(self) -> Path:
        return self.staging_root / ACTIVE_MODEL_POINTER_FILENAME

    def _write_active_pointer(
        self,
        *,
        model_version: str,
        artifact_digest: str,
        directory: Path,
        preprocessing_version: str,
    ) -> ActiveStagingPointer:
        self._validate_version(model_version, "active model version")
        self._validate_digest(artifact_digest, "active model digest")
        if directory.parent.resolve() != self.staging_root:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model directory is outside staging"
            )
        actual_digest = compute_artifact_digest(directory)
        if actual_digest != artifact_digest:
            raise StagingDeploymentError(
                "ACTIVE_STAGING_TAMPERED",
                "active staging artifact digest does not match its identity",
            )
        try:
            validate_supported_model_input_version(
                preprocessing_version, context="active model pointer"
            )
        except ValueError as exc:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model preprocessing is invalid"
            ) from exc
        pointer = ActiveStagingPointer(
            model_version=model_version,
            artifact_digest=artifact_digest,
            directory=directory.name,
            preprocessing_version=preprocessing_version,
        )
        temporary = self.active_pointer_path.with_name(
            f".{ACTIVE_MODEL_POINTER_FILENAME}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(
                    {
                        "artifact_version": "staging-pointer.v1",
                        "model_version": pointer.model_version,
                        "artifact_digest": pointer.artifact_digest,
                        "directory": pointer.directory,
                        "preprocessing_version": pointer.preprocessing_version,
                        "updated_at": self._clock()
                        .astimezone(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            os.replace(temporary, self.active_pointer_path)
        except OSError as exc:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_WRITE_FAILED", "active model pointer could not be saved"
            ) from exc
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
        return pointer

    def read_active_pointer(self) -> ActiveStagingPointer:
        payload = _read_json(
            self.active_pointer_path, code="ACTIVE_POINTER_INVALID"
        )
        if payload.get("artifact_version") != "staging-pointer.v1":
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model pointer version is invalid"
            )
        model_version = payload.get("model_version")
        artifact_digest = payload.get("artifact_digest")
        directory = payload.get("directory")
        preprocessing_version = payload.get("preprocessing_version")
        if (
            not isinstance(model_version, str)
            or not isinstance(artifact_digest, str)
            or not isinstance(directory, str)
            or not isinstance(preprocessing_version, str)
        ):
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model pointer is incomplete"
            )
        self._validate_version(model_version, "active model version")
        self._validate_digest(artifact_digest, "active model digest")
        if Path(directory).name != directory:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model directory is invalid"
            )
        try:
            validate_supported_model_input_version(
                preprocessing_version, context="active model pointer"
            )
        except ValueError as exc:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model preprocessing is invalid"
            ) from exc
        directory_path = (self.staging_root / directory).resolve()
        if directory_path.parent != self.staging_root:
            raise StagingDeploymentError(
                "ACTIVE_POINTER_INVALID", "active model directory is outside staging"
            )
        try:
            actual_digest = compute_artifact_digest(directory_path)
        except StagingDeploymentError as exc:
            raise StagingDeploymentError(
                "ACTIVE_STAGING_TAMPERED",
                "active staging artifact cannot be verified",
            ) from exc
        if actual_digest != artifact_digest:
            raise StagingDeploymentError(
                "ACTIVE_STAGING_TAMPERED",
                "active model pointer digest does not match the artifact",
            )
        return ActiveStagingPointer(
            model_version=model_version,
            artifact_digest=artifact_digest,
            directory=directory,
            preprocessing_version=preprocessing_version,
        )

    def _validate_artifact_files(self, artifact: Path) -> dict[str, Any]:
        if not artifact.is_dir() or artifact.is_symlink():
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_INVALID", "candidate artifact directory is invalid"
            )
        files = [path for path in artifact.iterdir()]
        if any(path.is_symlink() or not path.is_file() for path in files):
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_INVALID",
                "candidate artifact contains an unsafe entry",
            )
        names = {path.name for path in files}
        unexpected = names - ALLOWED_ARTIFACT_FILES
        if unexpected:
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_INVALID",
                "candidate artifact contains an unallowlisted file",
            )
        if not REQUIRED_ARTIFACT_FILES <= names:
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_INVALID", "candidate serving files are incomplete"
            )
        if not names & MODEL_WEIGHT_FILES or not names & TOKENIZER_FILES:
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_INVALID",
                "candidate model or tokenizer files are missing",
            )
        return _read_json(
            artifact / "serving_manifest.json", code="CANDIDATE_METADATA_INVALID"
        )

    def _validate_manifest(
        self,
        artifact: Path,
        *,
        expected_model_version: str,
        expected_preprocessing_version: str,
    ) -> dict[str, Any]:
        manifest = self._validate_artifact_files(artifact)
        if manifest.get("model_version") != expected_model_version:
            raise StagingDeploymentError(
                "CANDIDATE_MODEL_MISMATCH",
                "candidate model version does not match the reviewed run",
            )
        if manifest.get("run_dir_name") not in (None, expected_model_version):
            raise StagingDeploymentError(
                "CANDIDATE_MODEL_MISMATCH",
                "candidate serving manifest run identity does not match the "
                "reviewed run",
            )
        if manifest.get("model_key") != "distilbert":
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", "candidate model key is not supported"
            )
        if manifest.get("model_class") != "DistilBertForSequenceClassification":
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", "candidate model class is not supported"
            )
        if manifest.get("architecture") != "distilbert_sequence_classification":
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", "candidate architecture is not supported"
            )
        if manifest.get("model_input_hash_policy") != MODEL_INPUT_HASH_POLICY:
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID",
                "candidate model-input hash policy is incompatible",
            )
        try:
            preprocessing_version = validate_supported_model_input_version(
                manifest.get("preprocessing_version"),
                context="candidate serving manifest",
            )
        except ValueError as exc:
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID",
                "candidate preprocessing metadata is invalid",
            ) from exc
        if preprocessing_version != expected_preprocessing_version:
            raise StagingDeploymentError(
                "CANDIDATE_PREPROCESSING_MISMATCH",
                "candidate preprocessing is incompatible with the active model",
            )
        if manifest.get("label_names") != list(CANONICAL_LABELS):
            raise StagingDeploymentError(
                "CANDIDATE_LABEL_MAPPING_INVALID",
                "candidate label mapping is incompatible",
            )
        if manifest.get("num_labels") != len(CANONICAL_LABELS):
            raise StagingDeploymentError(
                "CANDIDATE_LABEL_MAPPING_INVALID",
                "candidate label count is incompatible",
            )
        if manifest.get("local_reload_verified") is not True:
            raise StagingDeploymentError(
                "CANDIDATE_NOT_RELOAD_VERIFIED",
                "candidate serving artifact lacks local reload proof",
            )
        model_revision = manifest.get("model_revision")
        if not isinstance(model_revision, str) or not model_revision.strip():
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", "candidate model revision is missing"
            )
        self._validate_manifest_file_hash(
            artifact,
            manifest,
            "checkpoint_file",
            "checkpoint_sha256",
        )
        self._validate_manifest_file_hash(
            artifact,
            manifest,
            "config_used_file",
            "config_used_sha256",
        )
        return manifest

    @staticmethod
    def _validate_manifest_file_hash(
        artifact: Path,
        manifest: Mapping[str, Any],
        file_field: str,
        hash_field: str,
    ) -> None:
        name = manifest.get(file_field)
        expected_digest = manifest.get(hash_field)
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name not in ALLOWED_ARTIFACT_FILES
            or not isinstance(expected_digest, str)
            or DIGEST_PATTERN.fullmatch(expected_digest) is None
        ):
            raise StagingDeploymentError(
                "CANDIDATE_METADATA_INVALID", "candidate file hash metadata is invalid"
            )
        path = artifact / name
        if not path.is_file() or sha256_file(path) != expected_digest:
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_TAMPERED", "candidate file hash verification failed"
            )

    def preflight_candidate(
        self,
        *,
        artifact_root: Path | str,
        run_id: str,
        expected_model_version: str,
        expected_model_digest: str,
        expected_preprocessing_version: str,
    ) -> StagingPreflight:
        self._validate_version(expected_model_version, "candidate model version")
        self._validate_digest(expected_model_digest, "candidate model digest")
        run_directory = get_run_artifact_directory(artifact_root, run_id)
        candidate_path = run_directory / CANDIDATE_ARTIFACT_DIR_NAME
        manifest = self._validate_manifest(
            candidate_path,
            expected_model_version=expected_model_version,
            expected_preprocessing_version=expected_preprocessing_version,
        )
        actual_digest = compute_artifact_digest(candidate_path)
        if actual_digest != expected_model_digest:
            raise StagingDeploymentError(
                "CANDIDATE_ARTIFACT_TAMPERED",
                "candidate artifact digest does not match the reviewed run",
            )
        self._load_and_verify(candidate_path, expected_model_version, reload=False)
        return StagingPreflight(
            run_id=run_id,
            candidate_path=candidate_path,
            candidate_model_version=expected_model_version,
            candidate_model_digest=actual_digest,
            preprocessing_version=str(manifest["preprocessing_version"]),
        )

    def _discover_active(
        self, expected_version: str, expected_preprocessing_version: str
    ) -> tuple[Path, str]:
        self._validate_version(expected_version, "active model version")
        if not self.staging_root.is_dir():
            raise StagingDeploymentError(
                "ACTIVE_STAGING_NOT_FOUND",
                "known-good local staging model was not found",
            )
        for path in sorted(self.staging_root.iterdir(), key=lambda item: item.name):
            if path.is_symlink() or not path.is_dir():
                continue
            manifest_path = path / "serving_manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = _read_json(manifest_path, code="ACTIVE_STAGING_INVALID")
            if manifest.get("model_version") == expected_version:
                self._validate_manifest(
                    path,
                    expected_model_version=expected_version,
                    expected_preprocessing_version=expected_preprocessing_version,
                )
                return path, compute_artifact_digest(path)
        raise StagingDeploymentError(
            "ACTIVE_STAGING_NOT_FOUND", "known-good local staging model was not found"
        )

    def prepare_deployment(
        self,
        *,
        artifact_root: Path | str,
        run_id: str,
        candidate_model_version: str,
        candidate_model_digest: str,
        active_model_version: str,
        active_model_digest: str,
        expected_preprocessing_version: str,
    ) -> StagingDeploymentPlan:
        preflight = self.preflight_candidate(
            artifact_root=artifact_root,
            run_id=run_id,
            expected_model_version=candidate_model_version,
            expected_model_digest=candidate_model_digest,
            expected_preprocessing_version=expected_preprocessing_version,
        )
        previous_path, previous_digest = self._discover_active(
            active_model_version, expected_preprocessing_version
        )
        self._validate_digest(active_model_digest, "active model digest")
        if previous_digest != active_model_digest:
            raise StagingDeploymentError(
                "ACTIVE_STAGING_TAMPERED",
                "active staging artifact does not match the reviewed model digest",
            )
        target_path = self.staging_root / candidate_model_version
        if target_path.exists():
            raise StagingDeploymentError(
                "STAGING_TARGET_EXISTS", "candidate staging target already exists"
            )
        timestamp = self._clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_name = f"{previous_path.name}__{timestamp}__{run_id[-12:]}"
        record = StagingDeploymentRecord(
            run_id=run_id,
            candidate_model_version=candidate_model_version,
            candidate_model_digest=candidate_model_digest,
            previous_staging_version=active_model_version,
            previous_staging_digest=previous_digest,
            previous_staging_dir_name=previous_path.name,
            archive_name=archive_name,
            active_model_version=active_model_version,
            active_model_digest=active_model_digest,
            preprocessing_version=expected_preprocessing_version,
        )
        return StagingDeploymentPlan(
            preflight=preflight,
            previous_staging_path=previous_path,
            previous_staging_version=active_model_version,
            previous_staging_digest=previous_digest,
            previous_staging_dir_name=previous_path.name,
            archive_name=archive_name,
            target_path=target_path,
            record=record,
        )

    def _load_and_verify(
        self, path: Path, expected_version: str, *, reload: bool
    ) -> None:
        callback = self._reload_callback if reload else self._load_validator
        try:
            result = callback(path, expected_version)
        except StagingDeploymentError:
            raise
        except Exception as exc:
            raise StagingDeploymentError(
                "STAGING_LOAD_FAILED", "local staging model load verification failed"
            ) from exc
        result_version = getattr(result, "model_version", result)
        if result_version is not None and str(result_version) != expected_version:
            raise StagingDeploymentError(
                "STAGING_MODEL_VERSION_MISMATCH",
                "loaded staging model version did not match the approved candidate",
            )

    def _archive_target(self, name: str) -> Path:
        if not name or len(name) > 240 or Path(name).name != name or ".." in name:
            raise StagingDeploymentError(
                "STAGING_PATH_INVALID", "staging archive name is invalid"
            )
        return self.archive_root / name

    def deploy(self, plan: StagingDeploymentPlan) -> StagingDeploymentRecord:
        self.staging_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)
        temporary_path = self.staging_root / (
            f".{plan.target_path.name}.{uuid.uuid4().hex}.tmp"
        )
        archive_path = self._archive_target(plan.archive_name)
        if archive_path.exists():
            raise StagingDeploymentError(
                "STAGING_ARCHIVE_EXISTS", "staging archive target already exists"
            )
        try:
            shutil.copytree(
                plan.preflight.candidate_path, temporary_path, symlinks=False
            )
            self._validate_manifest(
                temporary_path,
                expected_model_version=plan.preflight.candidate_model_version,
                expected_preprocessing_version=plan.preflight.preprocessing_version,
            )
            if (
                compute_artifact_digest(temporary_path)
                != plan.preflight.candidate_model_digest
            ):
                raise StagingDeploymentError(
                    "CANDIDATE_ARTIFACT_TAMPERED",
                    "candidate copy failed integrity verification",
                )
            os.replace(temporary_path, plan.target_path)
            try:
                self._load_and_verify(
                    plan.target_path,
                    plan.preflight.candidate_model_version,
                    reload=True,
                )
                self._write_active_pointer(
                    model_version=plan.preflight.candidate_model_version,
                    artifact_digest=plan.preflight.candidate_model_digest,
                    directory=plan.target_path,
                    preprocessing_version=plan.preflight.preprocessing_version,
                )
            except StagingDeploymentError as exc:
                self._restore_previous_after_failed_deploy(
                    plan,
                    archive_path=archive_path,
                    failure=exc,
                )
            # Keep the previous directory in place until the pointer names the
            # validated candidate. A process termination at any point before
            # the pointer replacement therefore leaves the old pointer valid.
            shutil.move(str(plan.previous_staging_path), str(archive_path))
            return StagingDeploymentRecord.from_payload(
                {**plan.record.to_payload(), "status": "DEPLOYED"}
            )
        except StagingDeploymentError:
            raise
        except Exception as exc:
            try:
                self._restore_previous_state(
                    plan,
                    archive_path=archive_path,
                )
            except Exception as restore_exc:
                raise StagingDeploymentError(
                    "STAGING_ROLLBACK_FAILED",
                    "local staging failure could not be safely restored",
                ) from restore_exc
            raise StagingDeploymentError(
                "STAGING_DEPLOY_FAILED",
                "local staging promotion failed; previous staging was restored",
                rolled_back=True,
            ) from exc
        finally:
            if temporary_path.exists():
                shutil.rmtree(temporary_path, ignore_errors=True)

    def _restore_previous_state(
        self,
        plan: StagingDeploymentPlan,
        *,
        archive_path: Path,
    ) -> None:
        if plan.target_path.is_dir():
            failed_target = self._archive_target(
                f"{plan.target_path.name}__failed__{plan.record.run_id[-12:]}"
            )
            if failed_target.exists():
                failed_target = self._archive_target(
                    f"{plan.target_path.name}__failed__{uuid.uuid4().hex}"
                )
            shutil.move(str(plan.target_path), str(failed_target))
        self._restore_if_archived(plan, archive_path)
        self._load_and_verify(
            plan.previous_staging_path,
            plan.previous_staging_version,
            reload=True,
        )
        self._write_active_pointer(
            model_version=plan.previous_staging_version,
            artifact_digest=plan.previous_staging_digest,
            directory=plan.previous_staging_path,
            preprocessing_version=plan.record.preprocessing_version,
        )

    def _restore_if_archived(
        self, plan: StagingDeploymentPlan, archive_path: Path
    ) -> None:
        if not archive_path.is_dir():
            return
        if plan.previous_staging_path.exists():
            return
        shutil.move(str(archive_path), str(plan.previous_staging_path))

    def _restore_previous_after_failed_deploy(
        self,
        plan: StagingDeploymentPlan,
        *,
        archive_path: Path,
        failure: StagingDeploymentError,
    ) -> None:
        try:
            self._restore_previous_state(plan, archive_path=archive_path)
        except Exception as exc:
            raise StagingDeploymentError(
                "STAGING_ROLLBACK_FAILED",
                "candidate deployment failed and known-good staging restore could "
                "not be verified",
            ) from exc
        raise StagingDeploymentError(
            failure.code,
            "candidate deployment failed; previous staging model was restored",
            rolled_back=True,
        )

    def reconcile_prepared_deployment(
        self, record: StagingDeploymentRecord
    ) -> StagingDeploymentRecord:
        """Discard a deployment that never switched the active pointer."""

        pointer = self.read_active_pointer()
        if (
            pointer.model_version != record.previous_staging_version
            or pointer.artifact_digest != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "DEPLOYMENT_RECOVERY_REQUIRED",
                "active staging does not prove that deployment was never activated",
            )
        previous_path = self.staging_root / record.previous_staging_dir_name
        if (
            not previous_path.is_dir()
            or compute_artifact_digest(previous_path)
            != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "DEPLOYMENT_RECOVERY_REQUIRED",
                "known-good staging could not be verified during recovery",
            )
        candidate_path = self.staging_root / record.candidate_model_version
        if candidate_path.exists():
            if (
                not candidate_path.is_dir()
                or compute_artifact_digest(candidate_path)
                != record.candidate_model_digest
            ):
                raise StagingDeploymentError(
                    "DEPLOYMENT_RECOVERY_REQUIRED",
                    "interrupted candidate staging artifact failed verification",
                )
            try:
                shutil.rmtree(candidate_path)
            except OSError as exc:
                raise StagingDeploymentError(
                    "DEPLOYMENT_RECOVERY_REQUIRED",
                    "interrupted candidate staging artifact could not be removed",
                ) from exc
        return StagingDeploymentRecord.from_payload(
            {**record.to_payload(), "status": "PREPARED"}
        )

    def reconcile_completed_rollback(
        self, record: StagingDeploymentRecord
    ) -> StagingDeploymentRecord:
        """Verify a rollback whose physical work completed before its audit write."""

        pointer = self.read_active_pointer()
        if (
            pointer.model_version != record.previous_staging_version
            or pointer.artifact_digest != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "ROLLBACK_RECOVERY_REQUIRED",
                "active staging does not prove that rollback completed",
            )
        previous_path = self.staging_root / record.previous_staging_dir_name
        if (
            not previous_path.is_dir()
            or compute_artifact_digest(previous_path)
            != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "ROLLBACK_RECOVERY_REQUIRED",
                "known-good staging could not be verified after rollback",
            )
        current_path = self.staging_root / record.candidate_model_version
        current_archive = self._archive_target(
            f"{current_path.name}__rollback__{record.run_id[-12:]}"
        )
        if current_path.exists():
            raise StagingDeploymentError(
                "ROLLBACK_NOT_COMPLETE",
                "rollback still has an active candidate directory",
            )
        if (
            not current_archive.is_dir()
            or compute_artifact_digest(current_archive)
            != record.candidate_model_digest
        ):
            raise StagingDeploymentError(
                "ROLLBACK_RECOVERY_REQUIRED",
                "rolled-back candidate artifact could not be verified",
            )
        return StagingDeploymentRecord.from_payload(
            {**record.to_payload(), "status": "ROLLED_BACK"}
        )

    def _restore_deployed_after_failed_rollback(
        self,
        record: StagingDeploymentRecord,
        *,
        current_path: Path,
        archive_path: Path,
        previous_path: Path,
        current_archive: Path,
        moved_previous_from_archive: bool,
    ) -> None:
        try:
            if current_archive.exists() and not current_path.exists():
                shutil.move(str(current_archive), str(current_path))
            if (
                moved_previous_from_archive
                and previous_path.exists()
                and not archive_path.exists()
            ):
                shutil.move(str(previous_path), str(archive_path))
            self._load_and_verify(
                current_path, record.candidate_model_version, reload=True
            )
            self._write_active_pointer(
                model_version=record.candidate_model_version,
                artifact_digest=record.candidate_model_digest,
                directory=current_path,
                preprocessing_version=record.preprocessing_version,
            )
        except Exception as exc:
            raise StagingDeploymentError(
                "ROLLBACK_RECOVERY_FAILED",
                "rollback failed and deployed staging recovery could not be "
                "verified",
            ) from exc

    def rollback(
        self,
        record: StagingDeploymentRecord,
        *,
        requested_previous_version: str,
    ) -> StagingDeploymentRecord:
        if requested_previous_version != record.previous_staging_version:
            raise StagingDeploymentError(
                "ROLLBACK_VERSION_MISMATCH",
                "rollback version does not match the reviewed deployment record",
            )
        current_path = self.staging_root / record.candidate_model_version
        archive_path = self._archive_target(record.archive_name)
        if not current_path.is_dir():
            raise StagingDeploymentError(
                "ROLLBACK_ARTIFACT_MISSING", "deployed candidate is not available"
            )
        if compute_artifact_digest(current_path) != record.candidate_model_digest:
            raise StagingDeploymentError(
                "ROLLBACK_ARTIFACT_TAMPERED",
                "deployed candidate failed integrity verification",
            )
        previous_path = self.staging_root / record.previous_staging_dir_name
        previous_in_staging = previous_path.is_dir()
        previous_in_archive = archive_path.is_dir()
        if not previous_in_staging and not previous_in_archive:
            raise StagingDeploymentError(
                "ROLLBACK_ARTIFACT_MISSING", "known-good staging is not available"
            )
        if (
            previous_in_staging
            and compute_artifact_digest(previous_path)
            != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "ROLLBACK_ARTIFACT_TAMPERED",
                "known-good staging artifact failed integrity verification",
            )
        if (
            previous_in_archive
            and compute_artifact_digest(archive_path)
            != record.previous_staging_digest
        ):
            raise StagingDeploymentError(
                "ROLLBACK_ARTIFACT_TAMPERED",
                "known-good staging archive failed integrity verification",
            )
        current_archive = self._archive_target(
            f"{current_path.name}__rollback__{record.run_id[-12:]}"
        )
        moved_previous_from_archive = False
        try:
            if not previous_in_staging:
                shutil.move(str(archive_path), str(previous_path))
                moved_previous_from_archive = True
            self._load_and_verify(
                previous_path, record.previous_staging_version, reload=True
            )
            # Keep the candidate directory until the pointer names the known
            # good predecessor. A termination here leaves the candidate pointer
            # and candidate directory valid for another recovery attempt.
            self._write_active_pointer(
                model_version=record.previous_staging_version,
                artifact_digest=record.previous_staging_digest,
                directory=previous_path,
                preprocessing_version=record.preprocessing_version,
            )
            shutil.move(str(current_path), str(current_archive))
            return StagingDeploymentRecord.from_payload(
                {**record.to_payload(), "status": "ROLLED_BACK"}
            )
        except StagingDeploymentError as exc:
            self._restore_deployed_after_failed_rollback(
                record,
                current_path=current_path,
                archive_path=archive_path,
                previous_path=previous_path,
                current_archive=current_archive,
                moved_previous_from_archive=moved_previous_from_archive,
            )
            raise StagingDeploymentError(
                exc.code,
                "rollback load verification failed; deployed candidate was restored",
            ) from exc
        except Exception as exc:
            self._restore_deployed_after_failed_rollback(
                record,
                current_path=current_path,
                archive_path=archive_path,
                previous_path=previous_path,
                current_archive=current_archive,
                moved_previous_from_archive=moved_previous_from_archive,
            )
            raise StagingDeploymentError(
                "ROLLBACK_FAILED", "local staging rollback failed"
            ) from exc

    @staticmethod
    def _default_load_validator(path: Path, expected_version: str) -> Any:
        from web_app.config import Settings
        from web_app.services.model_service import ModelService

        settings = Settings(
            database_url="sqlite+aiosqlite://",
            app_env="testing",
            model_path="unused",
            model_registry_path=str(path),
            api_secret_key="",
        )
        service = ModelService(settings)
        if service.model_version != expected_version:
            raise RuntimeError("loaded model version mismatch")
        response = service.predict("SELECT * FROM users WHERE id = 1")
        if (
            response.get("prediction") not in CANONICAL_LABELS
            or not isinstance(response.get("confidence"), (int, float))
            or not isfinite(float(response["confidence"]))
        ):
            raise RuntimeError("prediction smoke returned an invalid contract")
        return service


__all__ = [
    "ACTIVE_MODEL_POINTER_FILENAME",
    "ActiveStagingPointer",
    "CANDIDATE_ARTIFACT_DIR_NAME",
    "LocalStagingAdapter",
    "StagingDeploymentError",
    "StagingDeploymentPlan",
    "StagingDeploymentRecord",
    "StagingPreflight",
    "compute_artifact_digest",
]
