from __future__ import annotations

import gc
import hashlib
import json
import math
import random
import shutil
import time
import traceback
from collections.abc import Mapping
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import autocast
from torch.amp import GradScaler
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm
from transformers import (
    AutoTokenizer,
    DataCollatorWithPadding,
    get_cosine_schedule_with_warmup,
)

from ml_model.evaluation.metrics import (
    collect_logits_labels_loss,
    compute_per_class_metrics,
    confidence_band_summary_frame,
    evaluate_from_logits,
    fit_temperature_scaling,
    model_size_megabytes,
    per_class_recall_at_threshold_frame,
    save_confusion_matrix_artifacts,
    save_reliability_diagram_artifacts,
    threshold_security_summary,
    top_label_calibration_frame,
)
from ml_model.preprocessing.dataset_io import (
    checkpoint_dir,
    load_json,
    loss_variant_dir,
    model_run_dir,
    save_csv,
    save_json,
    save_numpy_artifacts,
    seed_run_dir,
)
from ml_model.training.losses import build_loss, compute_class_weights
from ml_model.training.model_factory import (
    build_model,
    infer_architecture_family,
    infer_head_type,
)
from ml_model.training.run_contract import canonical_json

SUMMARY_REQUIRED_KEYS = (
    "model_key",
    "loss_key",
    "seed",
    "best_epoch",
    "val_macro_f1",
    "test_macro_f1",
)

LATENCY_REQUIRED_KEYS = (
    "latency_mean_ms",
    "latency_std_ms",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_min_ms",
    "latency_max_ms",
)


def load_checkpoint_payload(checkpoint_path: Path, *, context: str) -> dict[str, Any]:
    """Load a training checkpoint using the safe weights-only path."""

    try:
        payload = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )
    except Exception as exc:
        raise ValueError(
            f"checkpoint_load_failed:{context}:{type(exc).__name__}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"checkpoint_not_object:{context}")

    state_dict = payload.get("model_state_dict")
    if not isinstance(state_dict, Mapping):
        raise ValueError(f"checkpoint_missing_model_state_dict:{context}")
    if not all(
        isinstance(key, str) and torch.is_tensor(value)
        for key, value in state_dict.items()
    ):
        raise ValueError(f"checkpoint_state_dict_invalid:{context}")
    return payload


def validate_checkpoint_identity(
    payload: Mapping[str, Any],
    *,
    expected_model_key: str,
    expected_seed: int,
    expected_loss_key: str,
    expected_architecture: str,
    expected_preprocessing_version: str,
    expected_contract_hash: str,
    expected_model_class: str | None = None,
    context: str = "checkpoint",
) -> str | None:
    """Return a clear identity mismatch reason, or None when it matches."""

    expected = {
        "model_key": expected_model_key,
        "seed": int(expected_seed),
        "loss_key": expected_loss_key,
        "architecture": expected_architecture,
        "preprocessing_version": expected_preprocessing_version,
        "run_contract_sha256": expected_contract_hash,
    }
    for field, expected_value in expected.items():
        if payload.get(field) != expected_value:
            reason_field = (
                "contract" if field == "run_contract_sha256" else field
            )
            return f"{context}_{reason_field}_mismatch"
    if expected_model_class is not None and payload.get("model_class") != expected_model_class:
        return f"{context}_model_class_mismatch"
    return None


def load_tokenizer_for_config(cfg: dict[str, Any]):
    """Load the tokenizer revision recorded in the run contract."""

    kwargs: dict[str, Any] = {"use_fast": True}
    if cfg.get("model_revision"):
        kwargs["revision"] = cfg["model_revision"]
    return AutoTokenizer.from_pretrained(cfg["model_id"], **kwargs)


@dataclass
class ConfirmatoryRunnerContext:
    df_train: pd.DataFrame
    df_val: pd.DataFrame
    df_test: pd.DataFrame
    text_col: str
    label_col: str
    label_names: list[str]
    num_classes: int
    dataset_version: str
    preprocessing_version: str
    model_input_hash_policy: str
    dataset_metadata: dict[str, Any]
    run_contract: dict[str, Any]
    run_contract_sha256: str
    model_contracts: dict[str, dict[str, Any]]

    run_kind: str
    run_name: str
    run_output_dir: Path
    run_status_path: Path
    run_progress_path: Path
    run_heartbeat_path: Path
    run_failure_log_path: Path

    model_registry: dict[str, dict[str, Any]]
    run_model_keys: list[str]
    benchmark_seeds: list[int]
    loss_keys_by_model: dict[str, list[str]]
    fixed_loss_key: str

    checkpoint_selection_rule: str
    deterministic_mode: bool
    resume_if_available: bool
    resume_checkpoint: Path | None
    skip_completed_seeds: bool
    force_rerun_seeds: bool
    allow_partial_aggregation: bool

    n_epochs: int
    early_stop_patience: int
    max_grad_norm: float
    log_every_steps: int
    heartbeat_every_steps: int
    ece_n_bins: int
    confidence_thresholds: list[float]

    dataloader_num_workers: int
    dataloader_prefetch_factor: int
    checkpoint_interval_epochs: int

    enable_split_hygiene_recompute: bool
    enable_truncation_evidence: bool
    enable_calibration: bool
    enable_threshold_security_artifacts: bool
    enable_reliability_diagrams: bool
    enable_latency_benchmark: bool
    generate_heavy_artifacts_during_training: bool
    generate_heavy_artifacts_after_training: bool

    latency_protocol: dict[str, int]

    split_summaries: dict[str, Any]
    split_hygiene_evidence: dict[str, Any]

    device: torch.device
    cuda_fp16: bool
    cuda_bf16: bool


class WAFDataset(Dataset):
    def __init__(self, precomputed: dict[str, Any], labels: pd.Series):
        self.input_ids = precomputed["input_ids"]
        self.attention_mask = precomputed["attention_mask"]
        self.labels = labels.reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "input_ids": torch.tensor(self.input_ids[idx], dtype=torch.long),
            "attention_mask": torch.tensor(self.attention_mask[idx], dtype=torch.long),
            "labels": torch.tensor(int(self.labels.iloc[idx]), dtype=torch.long),
        }


class FinalConfirmatoryRunner:
    def __init__(self, ctx: ConfirmatoryRunnerContext):
        self.ctx = ctx

        self.model_resource_cache: dict[str, dict[str, Any]] = {}

        self.run_failures: list[dict[str, Any]] | None = None
        self.model_run_tables: dict[str, pd.DataFrame] | None = None
        self.model_truncation_overview: dict[str, dict[str, Any]] | None = None

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_default(value: Any):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=self._json_default)
        tmp_path.replace(path)

    def append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=self._json_default) + "\n")

    def write_run_status(self, state: str, stage: str, **extra: Any) -> None:
        payload = {
            "state": str(state),
            "stage": str(stage),
            "run_kind": self.ctx.run_kind,
            "run_name": self.ctx.run_name,
            "updated_at": self.utc_now_iso(),
            **extra,
        }
        self.write_json_atomic(self.ctx.run_status_path, payload)

    def write_run_progress(self, stage: str, completed_models: int, completed_seeds: int, **extra: Any) -> None:
        payload = {
            "stage": str(stage),
            "completed_models": int(completed_models),
            "total_models": int(len(self.ctx.run_model_keys)),
            "completed_seeds": int(completed_seeds),
            "total_seeds": int(len(self.ctx.run_model_keys) * len(self.ctx.benchmark_seeds)),
            "updated_at": self.utc_now_iso(),
            **extra,
        }
        self.write_json_atomic(self.ctx.run_progress_path, payload)

    def write_run_heartbeat(self, event: str, **extra: Any) -> None:
        self.append_jsonl(
            self.ctx.run_heartbeat_path,
            {
                "timestamp": self.utc_now_iso(),
                "event": str(event),
                "run_kind": self.ctx.run_kind,
                "run_name": self.ctx.run_name,
                **extra,
            },
        )

    def set_runtime_state(
        self,
        run_failures: list[dict[str, Any]] | None,
        model_run_tables: dict[str, pd.DataFrame] | None,
        model_truncation_overview: dict[str, dict[str, Any]] | None,
    ) -> None:
        self.run_failures = run_failures if run_failures is not None else []
        self.model_run_tables = model_run_tables if model_run_tables is not None else {}
        self.model_truncation_overview = (
            model_truncation_overview if model_truncation_overview is not None else {}
        )

    def _ensure_runtime_state_initialized(self) -> None:
        missing = []
        if self.run_failures is None:
            missing.append("run_failures")
        if self.model_run_tables is None:
            missing.append("model_run_tables")
        if self.model_truncation_overview is None:
            missing.append("model_truncation_overview")
        if missing:
            raise RuntimeError(
                "Run the run-state discovery cell before model execution. "
                f"Missing runner state: {missing}"
            )

    def seed_everything(self, seed: int = 42, deterministic: bool = True) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.deterministic = bool(deterministic)
            torch.backends.cudnn.benchmark = not bool(deterministic)

        try:
            torch.use_deterministic_algorithms(bool(deterministic), warn_only=True)
        except Exception:
            pass

    @staticmethod
    def capture_rng_state() -> dict[str, Any]:
        numpy_state = np.random.get_state()
        python_state = random.getstate()
        state: dict[str, Any] = {
            "python": [
                int(python_state[0]),
                list(python_state[1]),
                None if python_state[2] is None else int(python_state[2]),
            ],
            "numpy": {
                "bit_generator": str(numpy_state[0]),
                "state": [int(value) for value in numpy_state[1].tolist()],
                "pos": int(numpy_state[2]),
                "has_gauss": int(numpy_state[3]),
                "cached_gaussian": float(numpy_state[4]),
            },
            "torch": torch.get_rng_state(),
        }
        if torch.cuda.is_available():
            state["cuda"] = torch.cuda.get_rng_state_all()
        return state

    @staticmethod
    def restore_rng_state(state: dict[str, Any]) -> None:
        if not state:
            return
        if "python" in state:
            python_state = state["python"]
            random.setstate(
                (
                    int(python_state[0]),
                    tuple(int(value) for value in python_state[1]),
                    None if python_state[2] is None else int(python_state[2]),
                )
            )
        if "numpy" in state:
            numpy_state = state["numpy"]
            np.random.set_state(
                (
                    str(numpy_state["bit_generator"]),
                    np.asarray(numpy_state["state"], dtype=np.uint32),
                    int(numpy_state["pos"]),
                    int(numpy_state["has_gauss"]),
                    float(numpy_state["cached_gaussian"]),
                )
            )
        if "torch" in state:
            torch.set_rng_state(state["torch"])
        if torch.cuda.is_available() and "cuda" in state:
            torch.cuda.set_rng_state_all(state["cuda"])

    def get_autocast_context(self):
        if self.ctx.device.type == "cuda":
            if self.ctx.cuda_fp16:
                return autocast(device_type="cuda", dtype=torch.float16)
            if self.ctx.cuda_bf16:
                return autocast(device_type="cuda", dtype=torch.bfloat16)
        return nullcontext()

    @staticmethod
    def build_optimizer(model: torch.nn.Module, lr: float, weight_decay: float) -> torch.optim.Optimizer:
        no_decay = ["bias", "LayerNorm.weight", "layer_norm.weight"]
        grouped_parameters = [
            {
                "params": [
                    p
                    for n, p in model.named_parameters()
                    if p.requires_grad and not any(nd in n for nd in no_decay)
                ],
                "weight_decay": weight_decay,
            },
            {
                "params": [
                    p
                    for n, p in model.named_parameters()
                    if p.requires_grad and any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.0,
            },
        ]
        return torch.optim.AdamW(grouped_parameters, lr=lr)

    @staticmethod
    def aggregate_numeric_columns(df: pd.DataFrame, exclude: list[str] | None = None) -> dict[str, float]:
        exclude = exclude or []
        numeric_cols = [
            col for col in df.select_dtypes(include=[np.number]).columns if col not in set(exclude)
        ]
        payload: dict[str, float] = {}
        for col in numeric_cols:
            series = df[col].dropna().astype(float)
            if series.empty:
                continue
            mean = float(series.mean())
            std = float(series.std(ddof=1)) if series.shape[0] > 1 else 0.0
            ci95 = float(1.96 * std / math.sqrt(series.shape[0])) if series.shape[0] > 1 else 0.0
            payload[f"{col}_mean"] = mean
            payload[f"{col}_std"] = std
            payload[f"{col}_ci95_lower"] = float(mean - ci95)
            payload[f"{col}_ci95_upper"] = float(mean + ci95)
        return payload

    @staticmethod
    def aggregate_per_class_metrics(frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame(
                columns=[
                    "label_id",
                    "label_name",
                    "precision_mean",
                    "recall_mean",
                    "f1_mean",
                    "support_sum",
                ]
            )

        merged = pd.concat(frames, ignore_index=True)
        grouped = (
            merged.groupby(["label_id", "label_name"], as_index=False)
            .agg(
                precision_mean=("precision", "mean"),
                precision_std=("precision", "std"),
                recall_mean=("recall", "mean"),
                recall_std=("recall", "std"),
                f1_mean=("f1", "mean"),
                f1_std=("f1", "std"),
                support_sum=("support", "sum"),
            )
            .sort_values(by="label_id")
            .reset_index(drop=True)
        )
        for col in ["precision_std", "recall_std", "f1_std"]:
            grouped[col] = grouped[col].fillna(0.0)
        return grouped

    @torch.no_grad()
    def benchmark_inference_latency(
        self,
        model: torch.nn.Module,
        sample_batch: dict[str, torch.Tensor],
        warmup_steps: int,
        measure_steps: int,
    ) -> dict[str, float | int]:
        model.eval()
        ids = sample_batch["input_ids"].to(self.ctx.device)
        mask = sample_batch["attention_mask"].to(self.ctx.device)

        for _ in range(int(warmup_steps)):
            with self.get_autocast_context():
                _ = model(input_ids=ids, attention_mask=mask)
        if self.ctx.device.type == "cuda":
            torch.cuda.synchronize()

        times_ms = []
        for _ in range(int(measure_steps)):
            t0 = time.perf_counter()
            with self.get_autocast_context():
                _ = model(input_ids=ids, attention_mask=mask)
            if self.ctx.device.type == "cuda":
                torch.cuda.synchronize()
            times_ms.append((time.perf_counter() - t0) * 1000.0)

        arr = np.asarray(times_ms, dtype=np.float64)
        return {
            "latency_mean_ms": float(np.mean(arr)),
            "latency_std_ms": float(np.std(arr)),
            "latency_p50_ms": float(np.percentile(arr, 50)),
            "latency_p95_ms": float(np.percentile(arr, 95)),
            "latency_min_ms": float(np.min(arr)),
            "latency_max_ms": float(np.max(arr)),
            "measure_steps": int(measure_steps),
        }

    def compute_token_length_stats(
        self,
        texts: list[str],
        tokenizer,
        max_len: int,
        chunk_size: int = 4096,
    ) -> dict[str, Any]:
        lengths: list[int] = []
        total = len(texts)
        for start in range(0, total, chunk_size):
            chunk = [str(text) for text in texts[start : start + chunk_size]]
            encoded = tokenizer(
                chunk,
                truncation=False,
                padding=False,
                add_special_tokens=True,
                return_attention_mask=False,
            )
            lengths.extend(len(ids) for ids in encoded["input_ids"])

        arr = np.asarray(lengths, dtype=np.int32)
        if arr.size == 0:
            return {
                "count": 0,
                "max_len": int(max_len),
                "mean": 0.0,
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "max": 0,
                "truncated_count": 0,
                "truncated_rate": 0.0,
            }

        truncated_count = int(np.sum(arr > max_len))
        return {
            "count": int(arr.size),
            "max_len": int(max_len),
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "max": int(np.max(arr)),
            "truncated_count": truncated_count,
            "truncated_rate": float(truncated_count / max(arr.size, 1)),
        }

    def build_truncation_evidence(self, tokenizer, max_len: int) -> dict[str, Any]:
        train_stats = self.compute_token_length_stats(
            self.ctx.df_train[self.ctx.text_col].tolist(), tokenizer, max_len=max_len
        )
        val_stats = self.compute_token_length_stats(
            self.ctx.df_val[self.ctx.text_col].tolist(), tokenizer, max_len=max_len
        )
        test_stats = self.compute_token_length_stats(
            self.ctx.df_test[self.ctx.text_col].tolist(), tokenizer, max_len=max_len
        )

        total_count = train_stats["count"] + val_stats["count"] + test_stats["count"]
        total_truncated = (
            train_stats["truncated_count"]
            + val_stats["truncated_count"]
            + test_stats["truncated_count"]
        )
        weighted_mean = (
            train_stats["mean"] * train_stats["count"]
            + val_stats["mean"] * val_stats["count"]
            + test_stats["mean"] * test_stats["count"]
        ) / max(total_count, 1)

        return {
            "enabled": True,
            "max_len": int(max_len),
            "splits": {
                "train": train_stats,
                "validation": val_stats,
                "test": test_stats,
            },
            "overall": {
                "count": int(total_count),
                "truncated_count": int(total_truncated),
                "truncated_rate": float(total_truncated / max(total_count, 1)),
                "weighted_mean_tokens": float(weighted_mean),
            },
        }

    def preprocess_split(self, df_split: pd.DataFrame, tokenizer, max_len: int) -> dict[str, Any]:
        encoded = tokenizer(
            list(df_split[self.ctx.text_col].astype(str).tolist()),
            truncation=True,
            max_length=max_len,
            padding=False,
            return_attention_mask=True,
        )
        return {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
        }

    def tokenize_all_splits(self, tokenizer, max_len: int):
        print("Tokenization started for train/validation/test splits ...")
        start = time.time()
        pre_train = self.preprocess_split(self.ctx.df_train, tokenizer, max_len)
        pre_val = self.preprocess_split(self.ctx.df_val, tokenizer, max_len)
        pre_test = self.preprocess_split(self.ctx.df_test, tokenizer, max_len)
        elapsed = float(time.time() - start)
        total_samples = int(len(self.ctx.df_train) + len(self.ctx.df_val) + len(self.ctx.df_test))
        throughput = float(total_samples / max(elapsed, 1e-9))
        print(
            f"Tokenization finished | samples={total_samples:,} | "
            f"elapsed={elapsed:.1f}s | throughput={throughput:.1f} samples/s"
        )
        return pre_train, pre_val, pre_test, elapsed, throughput

    def prepare_model_resources(self, cfg: dict[str, Any]) -> dict[str, Any]:
        model_key = cfg["model_key"]
        if model_key in self.model_resource_cache:
            print(f"Using cached resources for model={model_key}")
            return self.model_resource_cache[model_key]

        model_dir = model_run_dir(self.ctx.run_output_dir, model_key)
        print(f"Preparing tokenizer/resources for model={model_key} ({cfg['model_id']})")
        prep_start = time.time()

        tokenizer = load_tokenizer_for_config(cfg)
        pre_train, pre_val, pre_test, tokenization_sec, throughput = self.tokenize_all_splits(
            tokenizer, cfg["max_seq_len"]
        )

        if self.ctx.enable_truncation_evidence:
            truncation_evidence = self.build_truncation_evidence(tokenizer=tokenizer, max_len=cfg["max_seq_len"])
        else:
            truncation_evidence = {
                "enabled": False,
                "max_len": int(cfg["max_seq_len"]),
                "note": (
                    "Skipped explicit recomputation; upstream metadata governs "
                    "max_seq_len for confirmatory runs."
                ),
            }

        payload = {
            "model_key": model_key,
            "model_id": cfg["model_id"],
            "max_seq_len": int(cfg["max_seq_len"]),
            "tokenization_seconds": float(tokenization_sec),
            "tokenization_throughput_samples_per_sec": float(throughput),
            "prepared_at": self.utc_now_iso(),
        }
        save_json(model_dir / "tokenization_summary.json", payload)
        save_json(model_dir / "truncation_evidence.json", truncation_evidence)

        resources = {
            "tokenizer": tokenizer,
            "pre_train": pre_train,
            "pre_val": pre_val,
            "pre_test": pre_test,
            "truncation_evidence": truncation_evidence,
            "tokenization_summary": payload,
        }
        self.model_resource_cache[model_key] = resources

        print(
            f"Resources ready for model={model_key} | "
            f"elapsed={time.time() - prep_start:.1f}s | cache_size={len(self.model_resource_cache)}"
        )
        return resources

    def _base_loader_kwargs(self) -> dict[str, Any]:
        return {
            "num_workers": int(self.ctx.dataloader_num_workers),
            "pin_memory": self.ctx.device.type == "cuda",
        }

    @staticmethod
    def _epoch_shuffle_seed(seed: int, epoch: int) -> int:
        return int((int(seed) * 1_000_003 + int(epoch) * 97_003) % (2**31 - 1))

    def build_train_loader_for_epoch(
        self,
        resources: dict[str, Any],
        cfg: dict[str, Any],
        seed: int,
        epoch: int,
    ) -> DataLoader:
        collator = DataCollatorWithPadding(tokenizer=resources["tokenizer"], padding=True)
        generator = torch.Generator().manual_seed(self._epoch_shuffle_seed(int(seed), int(epoch)))

        loader_kwargs = self._base_loader_kwargs()
        if self.ctx.dataloader_num_workers > 0:
            loader_kwargs["persistent_workers"] = False
            loader_kwargs["prefetch_factor"] = int(self.ctx.dataloader_prefetch_factor)

        train_loader = DataLoader(
            WAFDataset(resources["pre_train"], self.ctx.df_train["label_id"]),
            batch_size=cfg["per_device_train_batch_size"],
            shuffle=True,
            generator=generator,
            collate_fn=collator,
            **loader_kwargs,
        )
        return train_loader

    def build_eval_loaders_and_latency_batch(
        self,
        resources: dict[str, Any],
        cfg: dict[str, Any],
    ):
        collator = DataCollatorWithPadding(tokenizer=resources["tokenizer"], padding=True)

        loader_kwargs = self._base_loader_kwargs()
        if self.ctx.dataloader_num_workers > 0:
            loader_kwargs["persistent_workers"] = True
            loader_kwargs["prefetch_factor"] = int(self.ctx.dataloader_prefetch_factor)

        eval_bs = cfg.get(
            "eval_batch_size",
            cfg["per_device_train_batch_size"] * cfg.get("eval_batch_multiplier", 2),
        )
        val_loader = DataLoader(
            WAFDataset(resources["pre_val"], self.ctx.df_val["label_id"]),
            batch_size=eval_bs,
            shuffle=False,
            collate_fn=collator,
            **loader_kwargs,
        )
        test_loader = DataLoader(
            WAFDataset(resources["pre_test"], self.ctx.df_test["label_id"]),
            batch_size=eval_bs,
            shuffle=False,
            collate_fn=collator,
            **loader_kwargs,
        )

        latency_loader = DataLoader(
            WAFDataset(resources["pre_test"], self.ctx.df_test["label_id"]),
            batch_size=int(self.ctx.latency_protocol["batch_size"]),
            shuffle=False,
            collate_fn=collator,
            **loader_kwargs,
        )
        latency_batch = next(iter(latency_loader))

        return val_loader, test_loader, latency_batch

    def build_seed_paths(
        self,
        variant_dir: Path,
        model_key: str,
        loss_key: str,
        seed: int,
    ) -> dict[str, Path]:
        seed_dir = seed_run_dir(variant_dir, seed)
        ckpt_dir = checkpoint_dir(seed_dir)
        return {
            "seed_dir": seed_dir,
            "ckpt_dir": ckpt_dir,
            "model_key": model_key,
            "loss_key": loss_key,
            "seed": int(seed),
            "best_ckpt": ckpt_dir / f"best_{model_key}_{loss_key}_seed{int(seed):04d}.pt",
            "last_ckpt": ckpt_dir / f"last_{model_key}_{loss_key}_seed{int(seed):04d}.pt",
            "config_metadata": seed_dir / "config_metadata.json",
            "history": seed_dir / "train_history.json",
            "summary": seed_dir / "summary_metrics.json",
            "calibration": seed_dir / "calibration.json",
            "status": seed_dir / "status.json",
            "progress": seed_dir / "progress.json",
            "heartbeat": seed_dir / "heartbeat.jsonl",
            "completed_marker": seed_dir / "completed.marker.json",
            "failed_marker": seed_dir / "failed.marker.json",
            "interrupted_marker": seed_dir / "interrupted.marker.json",
            "latency_summary": seed_dir / "latency_summary.json",
        }

    def validate_completed_seed_artifacts(
        self,
        paths: dict[str, Path],
    ) -> tuple[bool, str, dict[str, Any] | None]:
        if not paths["completed_marker"].exists():
            return False, "completed_marker_missing", None

        if not paths["config_metadata"].exists():
            return False, "config_metadata_missing", None

        if not paths["summary"].exists():
            return False, "summary_missing", None

        try:
            config_metadata = load_json(paths["config_metadata"])
            summary = load_json(paths["summary"])
        except Exception as exc:
            return False, f"metadata_load_failed:{type(exc).__name__}", None

        if not isinstance(config_metadata, dict):
            return False, "config_metadata_not_object", None

        if not isinstance(summary, dict):
            return False, "summary_not_object", None

        missing_keys = [key for key in SUMMARY_REQUIRED_KEYS if key not in summary]
        if missing_keys:
            return False, f"summary_missing_keys:{','.join(missing_keys)}", summary

        model_key = paths["model_key"]
        loss_key = paths["loss_key"]
        seed = int(paths["seed"])
        cfg = self.ctx.model_registry[model_key]
        expected = {
            "run_contract_sha256": self.ctx.run_contract_sha256,
            "model_key": model_key,
            "model_id": cfg["model_id"],
            "architecture": cfg["architecture"],
            "dataset_version": self.ctx.dataset_version,
            "preprocessing_version": self.ctx.preprocessing_version,
            "seed": seed,
            "loss_key": loss_key,
        }
        for field, expected_value in expected.items():
            for payload in (config_metadata, summary):
                if payload.get(field) != expected_value:
                    reason = {
                        "run_contract_sha256": "contract_mismatch",
                        "architecture": "architecture_mismatch",
                        "model_id": "model_id_mismatch",
                        "seed": "seed_mismatch",
                        "loss_key": "loss_key_mismatch",
                    }.get(field, f"{field}_mismatch")
                    return False, reason, summary

        expected_model_class = (
            "DistilBertForSequenceClassification"
            if cfg["architecture"] == "distilbert_sequence_classification"
            else None
        )
        if (
            expected_model_class
            and config_metadata.get("model_class") != expected_model_class
        ):
            return False, "model_class_mismatch", summary
        if expected_model_class and summary.get("model_class") != expected_model_class:
            return False, "model_class_mismatch", summary

        if not paths["best_ckpt"].exists():
            return False, "best_checkpoint_missing", summary

        try:
            checkpoint_payload = load_checkpoint_payload(
                paths["best_ckpt"], context="best"
            )
        except ValueError as exc:
            return False, str(exc), summary
        checkpoint_reason = validate_checkpoint_identity(
            checkpoint_payload,
            expected_model_key=model_key,
            expected_seed=seed,
            expected_loss_key=loss_key,
            expected_architecture=str(cfg["architecture"]),
            expected_preprocessing_version=self.ctx.preprocessing_version,
            expected_contract_hash=self.ctx.run_contract_sha256,
            expected_model_class=expected_model_class,
            context="checkpoint",
        )
        if checkpoint_reason is not None:
            return False, checkpoint_reason, summary

        return True, "ok", summary

    def is_seed_completed(self, paths: dict[str, Path]) -> bool:
        completed, _, _ = self.validate_completed_seed_artifacts(paths)
        return bool(completed)

    def load_completed_summary(self, paths: dict[str, Path]) -> dict[str, Any] | None:
        completed, _, summary = self.validate_completed_seed_artifacts(paths)
        return summary if completed else None

    def update_seed_status(self, paths: dict[str, Path], state: str, **extra: Any) -> None:
        payload = {
            "state": str(state),
            "updated_at": self.utc_now_iso(),
            **extra,
        }
        self.write_json_atomic(paths["status"], payload)

    def update_seed_progress(self, paths: dict[str, Path], **extra: Any) -> None:
        payload = {
            "updated_at": self.utc_now_iso(),
            **extra,
        }
        self.write_json_atomic(paths["progress"], payload)

    def append_seed_heartbeat(self, paths: dict[str, Path], event: str, **extra: Any) -> None:
        self.append_jsonl(
            paths["heartbeat"],
            {
                "timestamp": self.utc_now_iso(),
                "event": str(event),
                **extra,
            },
        )

    def mark_seed_failure(
        self,
        paths: dict[str, Path],
        state: str,
        error_message: str,
        traceback_text: str,
        **extra: Any,
    ) -> None:
        marker_path = paths["failed_marker"] if state == "failed" else paths["interrupted_marker"]
        payload = {
            "state": state,
            "error": error_message,
            "traceback": traceback_text,
            "updated_at": self.utc_now_iso(),
            **extra,
        }
        save_json(marker_path, payload)
        self.update_seed_status(paths, state, error=error_message, **extra)

    def clear_seed_run_state(self, paths: dict[str, Path]) -> None:
        seed_dir = paths["seed_dir"]
        if seed_dir.exists():
            shutil.rmtree(seed_dir)
        paths["ckpt_dir"].mkdir(parents=True, exist_ok=True)

    @torch.no_grad()
    def _load_valid_latency_summary(self, latency_path: Path) -> dict[str, Any] | None:
        if not latency_path.exists():
            return None
        try:
            payload = load_json(latency_path)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None

        for key in LATENCY_REQUIRED_KEYS:
            value = payload.get(key)
            if value is None:
                return None
            if not isinstance(value, (int, float)):
                return None

        return payload

    def _patch_summary_with_latency(
        self,
        summary_path: Path,
        latency_summary: dict[str, Any],
    ) -> None:
        if not summary_path.exists():
            return
        try:
            summary_payload = load_json(summary_path)
        except Exception:
            return
        if not isinstance(summary_payload, dict):
            return

        mapping = {
            "inference_latency_mean_ms": "latency_mean_ms",
            "inference_latency_std_ms": "latency_std_ms",
            "inference_latency_p50_ms": "latency_p50_ms",
            "inference_latency_p95_ms": "latency_p95_ms",
            "inference_latency_min_ms": "latency_min_ms",
            "inference_latency_max_ms": "latency_max_ms",
        }

        changed = False
        for summary_key, latency_key in mapping.items():
            new_value = latency_summary.get(latency_key)
            if summary_payload.get(summary_key) != new_value:
                summary_payload[summary_key] = new_value
                changed = True

        if changed:
            self.write_json_atomic(summary_path, summary_payload)

    def _compute_latency_from_best_checkpoint(
        self,
        cfg: dict[str, Any],
        loss_key: str,
        seed: int,
        variant_dir: Path,
        resources: dict[str, Any] | None,
    ) -> dict[str, Any]:
        model_key = cfg["model_key"]
        paths = self.build_seed_paths(
            variant_dir=variant_dir,
            model_key=model_key,
            loss_key=loss_key,
            seed=int(seed),
        )

        if not paths["best_ckpt"].exists():
            raise FileNotFoundError(
                f"Best checkpoint missing for deferred latency: {paths['best_ckpt']}"
            )

        checkpoint_payload = load_checkpoint_payload(
            paths["best_ckpt"], context="deferred_latency"
        )

        model = None
        try:
            model = build_model(cfg, self.ctx.num_classes, self.ctx.device)
            checkpoint_reason = validate_checkpoint_identity(
                checkpoint_payload,
                expected_model_key=model_key,
                expected_seed=int(seed),
                expected_loss_key=loss_key,
                expected_architecture=str(cfg["architecture"]),
                expected_preprocessing_version=self.ctx.preprocessing_version,
                expected_contract_hash=self.ctx.run_contract_sha256,
                expected_model_class=type(model).__name__,
                context="checkpoint",
            )
            if checkpoint_reason is not None:
                raise RuntimeError(f"Checkpoint identity mismatch: {checkpoint_reason}")
            model.load_state_dict(checkpoint_payload["model_state_dict"])

            if resources is None:
                resources = self.prepare_model_resources(cfg)
            _, _, latency_batch = self.build_eval_loaders_and_latency_batch(resources, cfg)
            latency_input = {
                "input_ids": latency_batch["input_ids"],
                "attention_mask": latency_batch["attention_mask"],
            }

            latency_summary = self.benchmark_inference_latency(
                model=model,
                sample_batch=latency_input,
                warmup_steps=int(self.ctx.latency_protocol["warmup_steps"]),
                measure_steps=int(self.ctx.latency_protocol["measure_steps"]),
            )
            return latency_summary
        finally:
            if model is not None:
                del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def train_one_epoch(
        self,
        model,
        dataloader,
        optimizer,
        scheduler,
        scaler,
        criterion,
        cfg: dict[str, Any],
        epoch: int,
        seed: int,
        paths: dict[str, Path],
    ):
        model.train()
        optimizer.zero_grad(set_to_none=True)

        n_steps = len(dataloader)
        accum_steps = cfg["gradient_accumulation_steps"]
        total_loss = 0.0
        epoch_start = time.time()

        pbar = tqdm(
            total=n_steps,
            desc=f"{cfg['model_key']}|seed{seed}|epoch{epoch}",
            dynamic_ncols=True,
            leave=False,
        )

        for step, batch in enumerate(dataloader, start=1):
            remainder_steps = n_steps % accum_steps
            actual_accum_steps = (
                remainder_steps
                if remainder_steps and step > n_steps - remainder_steps
                else accum_steps
            )
            ids = batch["input_ids"].to(
                self.ctx.device,
                non_blocking=(self.ctx.device.type == "cuda"),
            )
            mask = batch["attention_mask"].to(
                self.ctx.device,
                non_blocking=(self.ctx.device.type == "cuda"),
            )
            labels = batch["labels"].to(
                self.ctx.device,
                non_blocking=(self.ctx.device.type == "cuda"),
            )

            with self.get_autocast_context():
                logits = model(input_ids=ids, attention_mask=mask)["logits"]
                loss = criterion(logits, labels) / actual_accum_steps

            if not torch.isfinite(loss):
                raise RuntimeError(
                    "Non-finite loss detected | "
                    f"model={cfg['model_key']} | seed={seed} | epoch={epoch} | step={step} | "
                    f"loss={loss.item()}"
                )

            if scaler is not None:
                scaler.scale(loss).backward()
            else:
                loss.backward()
            total_loss += loss.item() * actual_accum_steps

            if (step % accum_steps == 0) or (step == n_steps):
                if scaler is not None:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), self.ctx.max_grad_norm
                    )
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), self.ctx.max_grad_norm
                    )
                    optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            pbar.update(1)

            if (step % self.ctx.log_every_steps == 0) or (step == n_steps):
                elapsed = time.time() - epoch_start
                steps_per_sec = float(step / max(elapsed, 1e-9))
                eta_sec = float((n_steps - step) / max(steps_per_sec, 1e-9))
                lr_now = float(scheduler.get_last_lr()[0])
                running_loss = float(total_loss / max(step, 1))
                print(
                    f"  step {step:>5,}/{n_steps:,} | loss={running_loss:.4f} | "
                    f"lr={lr_now:.2e} | speed={steps_per_sec:.2f} steps/s | eta={eta_sec:.1f}s"
                )
                self.update_seed_progress(
                    paths,
                    stage="train_epoch",
                    epoch=int(epoch),
                    step=int(step),
                    total_steps=int(n_steps),
                    running_train_loss=float(running_loss),
                    learning_rate=float(lr_now),
                    eta_sec=float(eta_sec),
                )

            if (step % self.ctx.heartbeat_every_steps == 0) or (step == n_steps):
                self.append_seed_heartbeat(
                    paths,
                    "train_step",
                    model_key=cfg["model_key"],
                    seed=int(seed),
                    epoch=int(epoch),
                    step=int(step),
                    total_steps=int(n_steps),
                )

        pbar.close()

        epoch_loss = float(total_loss / max(n_steps, 1))
        epoch_lr = float(scheduler.get_last_lr()[0])
        epoch_time_sec = float(time.time() - epoch_start)
        epoch_steps_per_sec = float(n_steps / max(epoch_time_sec, 1e-9))
        return epoch_loss, epoch_lr, epoch_time_sec, epoch_steps_per_sec

    def run_single_seed(
        self,
        cfg: dict[str, Any],
        loss_key: str,
        seed: int,
        variant_dir: Path,
        resources: dict[str, Any],
    ):
        model = None
        val_loader = None
        test_loader = None

        model_key = cfg["model_key"]
        paths = self.build_seed_paths(
            variant_dir=variant_dir,
            model_key=model_key,
            loss_key=loss_key,
            seed=int(seed),
        )

        try:
            completed_ok, completed_reason, completed_summary = self.validate_completed_seed_artifacts(paths)
            if completed_ok and self.ctx.skip_completed_seeds and not self.ctx.force_rerun_seeds:
                self.update_seed_status(
                    paths,
                    "skipped",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    reason="completed_marker_present_and_valid",
                )
                self.append_seed_heartbeat(
                    paths,
                    "seed_skipped",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                )
                print(f"[skip] model={model_key} | loss={loss_key} | seed={seed} already completed")
                return completed_summary

            if (
                paths["completed_marker"].exists()
                and not completed_ok
                and not self.ctx.force_rerun_seeds
            ):
                print(
                    "[completion-state-invalid] "
                    f"model={model_key} | loss={loss_key} | seed={seed} | reason={completed_reason}; "
                    "falling back to resume/fresh training"
                )

            if self.ctx.force_rerun_seeds:
                self.clear_seed_run_state(paths)
                print(
                    f"[force-rerun] cleared prior state | model={model_key} | loss={loss_key} | seed={seed}"
                )

            self.seed_everything(int(seed), deterministic=self.ctx.deterministic_mode)

            self.update_seed_status(
                paths,
                "running",
                stage="seed_start",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                resumed=False,
            )
            self.update_seed_progress(
                paths,
                stage="seed_start",
                epoch=0,
                total_epochs=int(cfg["num_train_epochs"]),
                step=0,
                total_steps=0,
            )
            self.append_seed_heartbeat(
                paths,
                "seed_start",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
            )
            self.write_run_heartbeat("seed_start", model_key=model_key, loss_key=loss_key, seed=int(seed))

            config_metadata = {
                "run_contract_sha256": self.ctx.run_contract_sha256,
                "run_contract": self.ctx.run_contract,
                "run_kind": self.ctx.run_kind,
                "run_name": self.ctx.run_name,
                "dataset_version": self.ctx.dataset_version,
                "preprocessing_version": self.ctx.preprocessing_version,
                "model_input_hash_policy": self.ctx.model_input_hash_policy,
                "dataset_metadata": self.ctx.dataset_metadata,
                "model_key": model_key,
                "model_version": f"{model_key}_{self.ctx.run_name}_seed{int(seed)}",
                "model_id": cfg["model_id"],
                "model_revision": cfg.get("model_revision", "unresolved"),
                "tokenizer_id": cfg["model_id"],
                "tokenizer_revision": cfg.get("model_revision", "unresolved"),
                "architecture": cfg["architecture"],
                "seed": int(seed),
                "loss_key": loss_key,
                "max_seq_len": int(cfg["max_seq_len"]),
                "checkpoint_selection_rule": self.ctx.checkpoint_selection_rule,
                "deterministic_mode": bool(self.ctx.deterministic_mode),
                "resume_if_available": bool(self.ctx.resume_if_available),
                "skip_completed_seeds": bool(self.ctx.skip_completed_seeds),
                "force_rerun_seeds": bool(self.ctx.force_rerun_seeds),
            }
            save_json(paths["seed_dir"] / "truncation_evidence.json", resources["truncation_evidence"])

            val_loader, test_loader, latency_batch = self.build_eval_loaders_and_latency_batch(resources, cfg)
            train_dataset = WAFDataset(resources["pre_train"], self.ctx.df_train["label_id"])

            train_batches_per_epoch = max(
                math.ceil(len(train_dataset) / max(int(cfg["per_device_train_batch_size"]), 1)),
                1,
            )
            print(
                f"[seed-start] model={model_key} | loss={loss_key} | seed={seed} | "
                f"train_batches={train_batches_per_epoch:,} | val_batches={len(val_loader):,} | "
                f"test_batches={len(test_loader):,}"
            )

            class_weights_np = compute_class_weights(
                self.ctx.df_train["label_id"].to_numpy(dtype=np.int64, copy=False),
                self.ctx.label_names,
            )
            criterion, _ = build_loss(
                loss_key=loss_key,
                class_weights=torch.tensor(class_weights_np, dtype=torch.float32, device=self.ctx.device),
                gamma=cfg.get("focal_gamma", 2.0),
            )

            model = build_model(cfg, self.ctx.num_classes, self.ctx.device)
            actual_model_class = type(model).__name__
            expected_model_class = (
                "DistilBertForSequenceClassification"
                if cfg["architecture"] == "distilbert_sequence_classification"
                else None
            )
            if expected_model_class and actual_model_class != expected_model_class:
                raise ValueError(
                    "Requested native DistilBERT architecture produced unexpected "
                    f"model class: {actual_model_class}"
                )
            model_config_sha256 = hashlib.sha256(
                canonical_json(model.config.to_dict()).encode("utf-8")
            ).hexdigest()
            tokenizer_identity = {
                "model_id": cfg["model_id"],
                "revision": cfg.get("model_revision", "unresolved"),
            }
            config_metadata.update(
                {
                    "architecture_family": infer_architecture_family(cfg["architecture"]),
                    "head_type": infer_head_type(cfg["architecture"]),
                    "model_class": actual_model_class,
                    "model_revision": cfg.get("model_revision", "unresolved"),
                    "tokenizer_id": cfg["model_id"],
                    "tokenizer_revision": cfg.get("model_revision", "unresolved"),
                    "model_config_sha256": model_config_sha256,
                    "tokenizer_identity": tokenizer_identity,
                }
            )
            save_json(paths["seed_dir"] / "config_metadata.json", config_metadata)
            optimizer = self.build_optimizer(model, cfg["learning_rate"], cfg["weight_decay"])
            scaler = GradScaler("cuda") if self.ctx.cuda_fp16 else None

            steps_per_epoch = max(
                math.ceil(train_batches_per_epoch / max(int(cfg["gradient_accumulation_steps"]), 1)),
                1,
            )
            total_steps = steps_per_epoch * cfg["num_train_epochs"]
            warmup_steps = int(cfg["warmup_ratio"] * total_steps)
            scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

            best_epoch = 0
            best_val_macro_f1 = -1.0
            best_val_loss = float("inf")
            no_improve = 0
            history: list[dict[str, Any]] = []
            start_epoch = 1

            resume_allowed = bool(self.ctx.resume_if_available and not self.ctx.force_rerun_seeds)
            resume_path = self.ctx.resume_checkpoint or paths["last_ckpt"]
            if resume_allowed and resume_path.exists():
                try:
                    resume_payload = load_checkpoint_payload(
                        resume_path, context="resume"
                    )
                except ValueError as exc:
                    raise RuntimeError(
                        f"Could not load resume checkpoint: {resume_path}"
                    ) from exc
                checkpoint_reason = validate_checkpoint_identity(
                    resume_payload,
                    expected_model_key=model_key,
                    expected_seed=int(seed),
                    expected_loss_key=loss_key,
                    expected_architecture=str(cfg["architecture"]),
                    expected_preprocessing_version=self.ctx.preprocessing_version,
                    expected_contract_hash=self.ctx.run_contract_sha256,
                    expected_model_class=actual_model_class,
                    context="resume_checkpoint",
                )
                if checkpoint_reason is not None:
                    raise RuntimeError(
                        f"Resume checkpoint identity mismatch: {checkpoint_reason}"
                    )
                required_keys = ["epoch", "model_state_dict", "optimizer_state_dict", "scheduler_state_dict"]
                missing_keys = [key for key in required_keys if key not in resume_payload]
                if missing_keys:
                    raise RuntimeError(
                        f"Resume checkpoint is incompatible ({resume_path}); "
                        f"missing keys: {', '.join(missing_keys)}"
                    )
                try:
                    model.load_state_dict(resume_payload["model_state_dict"])
                    optimizer.load_state_dict(resume_payload["optimizer_state_dict"])
                    scheduler.load_state_dict(resume_payload["scheduler_state_dict"])
                    if scaler is not None and resume_payload.get("scaler_state_dict"):
                        scaler.load_state_dict(resume_payload["scaler_state_dict"])
                except Exception as exc:
                    raise RuntimeError(
                        f"Resume checkpoint is incompatible with the selected model: {resume_path}"
                    ) from exc
                best_epoch = int(resume_payload.get("best_epoch", 0))
                best_val_macro_f1 = float(
                    resume_payload.get("best_val_macro_f1", -1.0)
                )
                best_val_loss = float(
                    resume_payload.get("best_val_loss", float("inf"))
                )
                no_improve = int(resume_payload.get("no_improve", 0))
                history = list(resume_payload.get("history", []))
                resume_epoch = int(resume_payload.get("epoch", 0))
                start_epoch = resume_epoch + 1
                self.restore_rng_state(resume_payload.get("rng_state", {}))
                print(
                    f"[resume] model={model_key} | loss={loss_key} | seed={seed} | "
                    f"resume_epoch={resume_epoch} -> start_epoch={start_epoch}"
                )
                self.update_seed_status(
                    paths,
                    "running",
                    stage="resume_loaded",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    resumed=True,
                    resumed_from_epoch=int(resume_epoch),
                )
                self.append_seed_heartbeat(
                    paths,
                    "resume_loaded",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    resume_epoch=int(resume_epoch),
                )

            run_start = time.time()

            if start_epoch > cfg["num_train_epochs"]:
                print(
                    f"[resume] model={model_key} | loss={loss_key} | seed={seed} already reached epoch boundary; "
                    "skipping training loop and moving to evaluation"
                )

            for epoch in range(start_epoch, cfg["num_train_epochs"] + 1):
                print(f"\nEpoch {epoch}/{cfg['num_train_epochs']} | model={model_key} | seed={seed}")
                self.update_seed_status(
                    paths,
                    "running",
                    stage="epoch_start",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    epoch=int(epoch),
                )

                train_loader = self.build_train_loader_for_epoch(
                    resources=resources,
                    cfg=cfg,
                    seed=int(seed),
                    epoch=int(epoch),
                )
                try:
                    train_loss, lr, epoch_time_sec, steps_per_sec = self.train_one_epoch(
                        model=model,
                        dataloader=train_loader,
                        optimizer=optimizer,
                        scheduler=scheduler,
                        scaler=scaler,
                        criterion=criterion,
                        cfg=cfg,
                        epoch=int(epoch),
                        seed=int(seed),
                        paths=paths,
                    )
                finally:
                    del train_loader
                    gc.collect()

                val_loss, val_logits, val_labels = collect_logits_labels_loss(
                    model=model,
                    dataloader=val_loader,
                    criterion=criterion,
                    device=self.ctx.device,
                    autocast_context_fn=self.get_autocast_context,
                )
                val_metrics = evaluate_from_logits(val_logits, val_labels, n_bins=self.ctx.ece_n_bins)

                improved = (val_metrics["macro_f1"] > best_val_macro_f1 + 1e-12) or (
                    abs(val_metrics["macro_f1"] - best_val_macro_f1) <= 1e-12 and val_loss < best_val_loss
                )

                if improved:
                    best_epoch = int(epoch)
                    best_val_macro_f1 = float(val_metrics["macro_f1"])
                    best_val_loss = float(val_loss)
                    no_improve = 0
                    torch.save(
                        {
                            "epoch": int(epoch),
                            "model_state_dict": deepcopy(model.state_dict()),
                            "best_val_macro_f1": float(best_val_macro_f1),
                            "best_val_loss": float(best_val_loss),
                            "cfg": cfg,
                            "loss_key": loss_key,
                            "seed": int(seed),
                            "model_key": model_key,
                            "architecture": cfg["architecture"],
                            "model_class": actual_model_class,
                            "preprocessing_version": self.ctx.preprocessing_version,
                            "run_contract_sha256": self.ctx.run_contract_sha256,
                        },
                        paths["best_ckpt"],
                    )
                    print(f"  best checkpoint saved: {paths['best_ckpt'].name}")
                    self.append_seed_heartbeat(
                        paths,
                        "best_checkpoint_saved",
                        model_key=model_key,
                        loss_key=loss_key,
                        seed=int(seed),
                        epoch=int(epoch),
                        val_macro_f1=float(best_val_macro_f1),
                        val_loss=float(best_val_loss),
                    )
                else:
                    no_improve += 1

                history_row = {
                    "epoch": int(epoch),
                    "learning_rate": float(lr),
                    "train_loss": float(train_loss),
                    "val_loss": float(val_loss),
                    "val_accuracy": float(val_metrics["accuracy"]),
                    "val_macro_f1": float(val_metrics["macro_f1"]),
                    "val_weighted_f1": float(val_metrics["weighted_f1"]),
                    "val_ece": float(val_metrics["ece"]),
                    "val_nll": float(val_metrics["nll"]),
                    "epoch_time_sec": float(epoch_time_sec),
                    "epoch_steps_per_sec": float(steps_per_sec),
                    "best_epoch_so_far": int(best_epoch),
                    "best_val_macro_f1_so_far": float(best_val_macro_f1),
                    "best_val_loss_so_far": float(best_val_loss),
                    "improved": bool(improved),
                }
                history.append(history_row)
                save_json(paths["history"], history)

                if (
                    epoch % self.ctx.checkpoint_interval_epochs == 0
                    or epoch == cfg["num_train_epochs"]
                ):
                    torch.save(
                        {
                            "epoch": int(epoch),
                            "model_state_dict": model.state_dict(),
                            "optimizer_state_dict": optimizer.state_dict(),
                            "scheduler_state_dict": scheduler.state_dict(),
                            "scaler_state_dict": (
                                scaler.state_dict() if scaler is not None else None
                            ),
                            "best_epoch": int(best_epoch),
                            "best_val_macro_f1": float(best_val_macro_f1),
                            "best_val_loss": float(best_val_loss),
                            "no_improve": int(no_improve),
                            "history": history,
                            "cfg": cfg,
                            "seed": int(seed),
                            "loss_key": loss_key,
                            "model_key": model_key,
                            "architecture": cfg["architecture"],
                            "model_class": actual_model_class,
                            "preprocessing_version": self.ctx.preprocessing_version,
                            "run_contract_sha256": self.ctx.run_contract_sha256,
                            "rng_state": self.capture_rng_state(),
                            "saved_at": self.utc_now_iso(),
                        },
                        paths["last_ckpt"],
                    )
                    print(f"  last checkpoint saved: {paths['last_ckpt'].name}")

                elapsed = float(time.time() - run_start)
                best_flag = "BEST" if improved else "NOT_BEST"
                print(
                    f"  epoch-summary | model={model_key} | seed={seed} | epoch={epoch}/{cfg['num_train_epochs']} | "
                    f"train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | val_macro_f1={val_metrics['macro_f1']:.4f} | "
                    f"lr={lr:.2e} | epoch_time={epoch_time_sec:.1f}s | elapsed={elapsed:.1f}s | state={best_flag}"
                )

                self.update_seed_status(
                    paths,
                    "running",
                    stage="epoch_end",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    epoch=int(epoch),
                    best_epoch=int(best_epoch),
                    best_val_macro_f1=float(best_val_macro_f1),
                    best_val_loss=float(best_val_loss),
                    epochs_without_improvement=int(no_improve),
                )
                self.update_seed_progress(
                    paths,
                    stage="epoch_end",
                    epoch=int(epoch),
                    total_epochs=int(cfg["num_train_epochs"]),
                    train_loss=float(train_loss),
                    val_loss=float(val_loss),
                    val_macro_f1=float(val_metrics["macro_f1"]),
                    learning_rate=float(lr),
                    epoch_time_sec=float(epoch_time_sec),
                    elapsed_sec=float(elapsed),
                    best_epoch=int(best_epoch),
                )
                self.append_seed_heartbeat(
                    paths,
                    "epoch_end",
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                    epoch=int(epoch),
                    train_loss=float(train_loss),
                    val_loss=float(val_loss),
                    val_macro_f1=float(val_metrics["macro_f1"]),
                    best_epoch=int(best_epoch),
                    improved=bool(improved),
                )

                if no_improve >= self.ctx.early_stop_patience:
                    print(
                        f"  early stop triggered | no_improve={no_improve} | "
                        f"patience={self.ctx.early_stop_patience} | best_epoch={best_epoch}"
                    )
                    self.append_seed_heartbeat(
                        paths,
                        "early_stop",
                        model_key=model_key,
                        loss_key=loss_key,
                        seed=int(seed),
                        epoch=int(epoch),
                        no_improve=int(no_improve),
                        patience=int(self.ctx.early_stop_patience),
                    )
                    break

            if not paths["best_ckpt"].exists():
                raise RuntimeError(
                    f"Best checkpoint was not produced for model={model_key}, loss={loss_key}, seed={seed}."
                )

            best_payload = load_checkpoint_payload(
                paths["best_ckpt"], context="best"
            )
            model.load_state_dict(best_payload["model_state_dict"])

            _, best_val_logits, best_val_labels = collect_logits_labels_loss(
                model=model,
                dataloader=val_loader,
                criterion=criterion,
                device=self.ctx.device,
                autocast_context_fn=self.get_autocast_context,
            )
            _, test_logits, test_labels = collect_logits_labels_loss(
                model=model,
                dataloader=test_loader,
                criterion=criterion,
                device=self.ctx.device,
                autocast_context_fn=self.get_autocast_context,
            )

            val_uncal = evaluate_from_logits(best_val_logits, best_val_labels, n_bins=self.ctx.ece_n_bins)
            test_uncal = evaluate_from_logits(test_logits, test_labels, n_bins=self.ctx.ece_n_bins)

            temperature = 1.0
            if self.ctx.enable_calibration:
                temperature = fit_temperature_scaling(best_val_logits, best_val_labels, device=self.ctx.device)
                val_cal = evaluate_from_logits(best_val_logits / temperature, best_val_labels, n_bins=self.ctx.ece_n_bins)
                test_cal = evaluate_from_logits(test_logits / temperature, test_labels, n_bins=self.ctx.ece_n_bins)
            else:
                val_cal = val_uncal
                test_cal = test_uncal

            save_numpy_artifacts(
                paths["seed_dir"] / "validation_outputs.npz",
                logits=best_val_logits,
                labels=best_val_labels,
                preds=val_uncal["preds"],
                probs=val_uncal["probs"],
                calibrated_probs=val_cal["probs"],
            )
            save_numpy_artifacts(
                paths["seed_dir"] / "test_outputs.npz",
                logits=test_logits,
                labels=test_labels,
                preds=test_uncal["preds"],
                probs=test_uncal["probs"],
                calibrated_probs=test_cal["probs"],
            )

            per_class = compute_per_class_metrics(test_labels, test_uncal["preds"], self.ctx.label_names)
            save_json(paths["seed_dir"] / "per_class_metrics.json", per_class)

            save_confusion_matrix_artifacts(
                labels=test_labels,
                preds=test_uncal["preds"],
                label_names=self.ctx.label_names,
                csv_path=paths["seed_dir"] / "confusion_matrix.csv",
                png_path=paths["seed_dir"] / "confusion_matrix.png",
                title=f"{model_key} confusion | {loss_key} | seed {seed}",
            )

            if self.ctx.enable_threshold_security_artifacts:
                security_views = threshold_security_summary(
                    labels=test_labels,
                    preds=test_cal["preds"],
                    probs=test_cal["probs"],
                    label_names=self.ctx.label_names,
                    normal_label="Normal",
                )
                save_csv(
                    security_views["attack_to_normal_by_class"],
                    paths["seed_dir"] / "attack_to_normal_fn.csv",
                    index=False,
                )
                save_csv(
                    confidence_band_summary_frame(test_labels, test_uncal["preds"], test_cal["probs"]),
                    paths["seed_dir"] / "confidence_band_summary.csv",
                    index=False,
                )
                save_csv(
                    per_class_recall_at_threshold_frame(
                        test_labels,
                        test_cal["preds"],
                        test_cal["probs"],
                        self.ctx.label_names,
                        self.ctx.confidence_thresholds,
                    ),
                    paths["seed_dir"] / "per_class_recall_at_threshold.csv",
                    index=False,
                )
                save_json(
                    paths["seed_dir"] / "security_summary.json",
                    {
                        "normal_false_positive": security_views["normal_false_positive"],
                        "attack_escape_total": security_views["attack_escape_total"],
                        "confidence_thresholds": self.ctx.confidence_thresholds,
                    },
                )
                normal_false_positive_rate = float(
                    security_views["normal_false_positive"]["normal_false_positive_rate"]
                )
                attack_escape_rate = float(security_views["attack_escape_total"]["attack_escape_rate"])
            else:
                normal_false_positive_rate = None
                attack_escape_rate = None

            if self.ctx.generate_heavy_artifacts_during_training and self.ctx.enable_reliability_diagrams:
                save_reliability_diagram_artifacts(
                    probs=test_uncal["probs"],
                    labels=test_labels,
                    csv_path=paths["seed_dir"] / "reliability_uncalibrated.csv",
                    png_path=paths["seed_dir"] / "reliability_uncalibrated.png",
                    n_bins=self.ctx.ece_n_bins,
                    title=f"{model_key} reliability uncalibrated",
                )
                save_reliability_diagram_artifacts(
                    probs=test_cal["probs"],
                    labels=test_labels,
                    csv_path=paths["seed_dir"] / "reliability_calibrated.csv",
                    png_path=paths["seed_dir"] / "reliability_calibrated.png",
                    n_bins=self.ctx.ece_n_bins,
                    title=f"{model_key} reliability calibrated",
                )
                save_csv(
                    top_label_calibration_frame(test_uncal["probs"], test_labels, self.ctx.label_names),
                    paths["seed_dir"] / "top_label_calibration_uncalibrated.csv",
                    index=False,
                )
                save_csv(
                    top_label_calibration_frame(test_cal["probs"], test_labels, self.ctx.label_names),
                    paths["seed_dir"] / "top_label_calibration_calibrated.csv",
                    index=False,
                )

            latency_summary: dict[str, Any] = {
                "latency_mean_ms": None,
                "latency_std_ms": None,
                "latency_p50_ms": None,
                "latency_p95_ms": None,
                "latency_min_ms": None,
                "latency_max_ms": None,
            }
            if self.ctx.generate_heavy_artifacts_during_training and self.ctx.enable_latency_benchmark:
                latency_input = {
                    "input_ids": latency_batch["input_ids"],
                    "attention_mask": latency_batch["attention_mask"],
                }
                latency_summary = self.benchmark_inference_latency(
                    model=model,
                    sample_batch=latency_input,
                    warmup_steps=int(self.ctx.latency_protocol["warmup_steps"]),
                    measure_steps=int(self.ctx.latency_protocol["measure_steps"]),
                )
                save_json(
                    paths["latency_summary"],
                    {**latency_summary, "latency_protocol": self.ctx.latency_protocol},
                )

            runtime_sec = float(time.time() - run_start)
            mean_epoch_sec = float(np.mean([row["epoch_time_sec"] for row in history])) if history else 0.0

            summary = {
                "run_contract_sha256": self.ctx.run_contract_sha256,
                "dataset_version": self.ctx.dataset_version,
                "preprocessing_version": self.ctx.preprocessing_version,
                "model_key": model_key,
                "model_id": cfg["model_id"],
                "model_revision": cfg.get("model_revision", "unresolved"),
                "tokenizer_id": cfg["model_id"],
                "tokenizer_revision": cfg.get("model_revision", "unresolved"),
                "model_config_sha256": model_config_sha256,
                "tokenizer_identity": tokenizer_identity,
                "architecture": cfg["architecture"],
                "architecture_family": infer_architecture_family(cfg["architecture"]),
                "head_type": infer_head_type(cfg["architecture"]),
                "model_class": type(model).__name__,
                "experiment_phase": cfg["experiment_phase"],
                "loss_key": loss_key,
                "seed": int(seed),
                "best_epoch": int(best_payload.get("epoch", best_epoch)),
                "val_accuracy": float(val_uncal["accuracy"]),
                "val_balanced_accuracy": float(val_uncal["balanced_accuracy"]),
                "val_macro_f1": float(val_uncal["macro_f1"]),
                "val_weighted_f1": float(val_uncal["weighted_f1"]),
                "val_ece_uncalibrated": float(val_uncal["ece"]),
                "val_ece_calibrated": float(val_cal["ece"]),
                "val_nll_uncalibrated": float(val_uncal["nll"]),
                "val_nll_calibrated": float(val_cal["nll"]),
                "val_brier_uncalibrated": float(val_uncal["brier_score"]),
                "val_brier_calibrated": float(val_cal["brier_score"]),
                "test_accuracy": float(test_uncal["accuracy"]),
                "test_balanced_accuracy": float(test_uncal["balanced_accuracy"]),
                "test_macro_f1": float(test_uncal["macro_f1"]),
                "test_weighted_f1": float(test_uncal["weighted_f1"]),
                "test_ece_uncalibrated": float(test_uncal["ece"]),
                "test_ece_calibrated": float(test_cal["ece"]),
                "test_nll_uncalibrated": float(test_uncal["nll"]),
                "test_nll_calibrated": float(test_cal["nll"]),
                "test_brier_uncalibrated": float(test_uncal["brier_score"]),
                "test_brier_calibrated": float(test_cal["brier_score"]),
                "normal_false_positive_rate": normal_false_positive_rate,
                "attack_escape_rate": attack_escape_rate,
                "inference_latency_mean_ms": latency_summary["latency_mean_ms"],
                "inference_latency_std_ms": latency_summary["latency_std_ms"],
                "inference_latency_p50_ms": latency_summary["latency_p50_ms"],
                "inference_latency_p95_ms": latency_summary["latency_p95_ms"],
                "inference_latency_min_ms": latency_summary["latency_min_ms"],
                "inference_latency_max_ms": latency_summary["latency_max_ms"],
                "model_size_mb": float(model_size_megabytes(model)),
                "training_workflow_runtime_sec": float(runtime_sec),
                "mean_epoch_training_time_sec": float(mean_epoch_sec),
            }

            save_json(paths["summary"], summary)
            save_json(
                paths["calibration"],
                {
                    "method": "temperature_scaling" if self.ctx.enable_calibration else "disabled",
                    "temperature": float(temperature),
                    "val_ece_uncalibrated": float(val_uncal["ece"]),
                    "val_ece_calibrated": float(val_cal["ece"]),
                    "test_ece_uncalibrated": float(test_uncal["ece"]),
                    "test_ece_calibrated": float(test_cal["ece"]),
                },
            )

            completion_payload = {
                "run_contract_sha256": self.ctx.run_contract_sha256,
                "architecture": cfg["architecture"],
                "model_id": cfg["model_id"],
                "completed_at": self.utc_now_iso(),
                "model_key": model_key,
                "loss_key": loss_key,
                "seed": int(seed),
                "best_epoch": int(summary["best_epoch"]),
                "summary_path": str(paths["summary"]),
                "checkpoint_best": str(paths["best_ckpt"]),
                "checkpoint_last": str(paths["last_ckpt"]),
            }
            save_json(paths["completed_marker"], completion_payload)

            self.update_seed_status(
                paths,
                "completed",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                best_epoch=int(summary["best_epoch"]),
                runtime_sec=float(runtime_sec),
            )
            self.update_seed_progress(
                paths,
                stage="completed",
                epoch=int(summary["best_epoch"]),
                total_epochs=int(cfg["num_train_epochs"]),
                runtime_sec=float(runtime_sec),
                val_macro_f1=float(summary["val_macro_f1"]),
                test_macro_f1=float(summary["test_macro_f1"]),
                percent=100.0,
            )
            self.append_seed_heartbeat(
                paths,
                "seed_completed",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                best_epoch=int(summary["best_epoch"]),
                runtime_sec=float(runtime_sec),
            )
            self.write_run_heartbeat(
                "seed_completed",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                best_epoch=int(summary["best_epoch"]),
                runtime_sec=float(runtime_sec),
            )

            print(
                f"[seed-complete] model={model_key} | loss={loss_key} | seed={seed} | "
                f"best_epoch={summary['best_epoch']} | val_macro_f1={summary['val_macro_f1']:.4f} | "
                f"test_macro_f1={summary['test_macro_f1']:.4f} | runtime={runtime_sec:.1f}s"
            )
            return summary

        except KeyboardInterrupt:
            tb = traceback.format_exc()
            self.mark_seed_failure(
                paths,
                "interrupted",
                "KeyboardInterrupt",
                tb,
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
            )
            self.append_seed_heartbeat(
                paths,
                "seed_interrupted",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
            )
            self.write_run_heartbeat(
                "seed_interrupted",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
            )
            raise
        except Exception as exc:
            tb = traceback.format_exc()
            self.mark_seed_failure(
                paths,
                "failed",
                str(exc),
                tb,
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
            )
            self.append_seed_heartbeat(
                paths,
                "seed_failed",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                error=str(exc),
            )
            self.write_run_heartbeat(
                "seed_failed",
                model_key=model_key,
                loss_key=loss_key,
                seed=int(seed),
                error=str(exc),
            )
            raise
        finally:
            if val_loader is not None:
                del val_loader
            if test_loader is not None:
                del test_loader
            if model is not None:
                del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def aggregate_variant_from_disk(self, cfg: dict[str, Any], loss_key: str, variant_dir: Path):
        seed_rows: list[dict[str, Any]] = []
        per_class_frames: list[pd.DataFrame] = []

        for seed in self.ctx.benchmark_seeds:
            paths = self.build_seed_paths(
                variant_dir=variant_dir,
                model_key=cfg["model_key"],
                loss_key=loss_key,
                seed=int(seed),
            )
            completed_ok, completed_reason, summary_payload = (
                self.validate_completed_seed_artifacts(paths)
            )
            if not completed_ok:
                if paths["completed_marker"].exists():
                    raise ValueError(
                        "Cannot aggregate incompatible completed seed artifacts: "
                        f"{paths['seed_dir']} ({completed_reason})"
                    )
                continue
            if summary_payload is None:
                continue

            seed_rows.append(summary_payload)

            per_class_path = paths["seed_dir"] / "per_class_metrics.json"
            if per_class_path.exists():
                frame = pd.DataFrame(load_json(per_class_path))
                if not frame.empty:
                    frame["seed"] = int(seed)
                    per_class_frames.append(frame)

        if not seed_rows:
            return None

        seed_df = pd.DataFrame(seed_rows).sort_values(by="seed").reset_index(drop=True)
        contract_hashes = set(seed_df["run_contract_sha256"].dropna().astype(str))
        if contract_hashes != {self.ctx.run_contract_sha256}:
            raise ValueError(
                "Cannot aggregate seed summaries with mixed contract hashes"
            )
        architectures = set(seed_df["architecture"].dropna().astype(str))
        if architectures != {str(cfg["architecture"])}:
            raise ValueError(
                "Cannot aggregate seed summaries with mixed architectures"
            )
        save_csv(seed_df, variant_dir / "seed_summaries.csv", index=False)

        aggregate_payload = {
            "model_key": cfg["model_key"],
            "loss_key": loss_key,
            "fixed_loss_key": self.ctx.fixed_loss_key,
            "n_seeds": int(seed_df.shape[0]),
            **self.aggregate_numeric_columns(seed_df, exclude=["seed"]),
        }
        save_json(variant_dir / "aggregate_summary.json", aggregate_payload)

        per_class_agg = self.aggregate_per_class_metrics(per_class_frames)
        save_csv(per_class_agg, variant_dir / "per_class_summary_aggregated.csv", index=False)

        return {
            "model_key": cfg["model_key"],
            "loss_key": loss_key,
            "architecture": next(iter(architectures)),
            "architecture_family": infer_architecture_family(
                next(iter(architectures))
            ),
            "head_type": infer_head_type(next(iter(architectures))),
            "experiment_phase": cfg["experiment_phase"],
            **aggregate_payload,
        }

    def aggregate_model_from_disk(self, model_key: str) -> pd.DataFrame:
        cfg = self.ctx.model_registry[model_key]
        model_dir = model_run_dir(self.ctx.run_output_dir, model_key)

        rows = []
        for loss_key in self.ctx.loss_keys_by_model[model_key]:
            variant_dir = loss_variant_dir(model_dir, loss_key)
            row = self.aggregate_variant_from_disk(cfg, loss_key, variant_dir)
            if row is not None:
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        model_df = pd.DataFrame(rows)
        sort_cols = [
            col for col in ["test_macro_f1_mean", "val_macro_f1_mean"] if col in model_df.columns
        ]
        if sort_cols:
            model_df = model_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)
        save_csv(model_df, model_dir / "loss_variant_aggregates.csv", index=False)
        return model_df

    def count_completed_seed_runs(self) -> int:
        completed = 0
        for model_key in self.ctx.run_model_keys:
            model_dir = model_run_dir(self.ctx.run_output_dir, model_key)
            for loss_key in self.ctx.loss_keys_by_model[model_key]:
                variant_dir = loss_variant_dir(model_dir, loss_key)
                for seed in self.ctx.benchmark_seeds:
                    paths = self.build_seed_paths(
                        variant_dir=variant_dir,
                        model_key=model_key,
                        loss_key=loss_key,
                        seed=int(seed),
                    )
                    if self.is_seed_completed(paths):
                        completed += 1
        return int(completed)

    def _model_has_completed_rows(self, model_key: str) -> bool:
        model_dir = model_run_dir(self.ctx.run_output_dir, model_key)
        for loss_key in self.ctx.loss_keys_by_model[model_key]:
            variant_dir = loss_variant_dir(model_dir, loss_key)
            for seed in self.ctx.benchmark_seeds:
                paths = self.build_seed_paths(
                    variant_dir=variant_dir,
                    model_key=model_key,
                    loss_key=loss_key,
                    seed=int(seed),
                )
                if self.is_seed_completed(paths):
                    return True
        return False

    def count_completed_models(self) -> int:
        self._ensure_runtime_state_initialized()

        count = 0
        for model_key in self.ctx.run_model_keys:
            cached_df = self.model_run_tables.get(model_key)
            if isinstance(cached_df, pd.DataFrame):
                if not cached_df.empty:
                    count += 1
                continue

            if self._model_has_completed_rows(model_key):
                count += 1

        return int(count)

    def seed_run_state(self, model_key: str, loss_key: str, seed: int) -> str:
        variant_dir = loss_variant_dir(model_run_dir(self.ctx.run_output_dir, model_key), loss_key)
        paths = self.build_seed_paths(
            variant_dir=variant_dir,
            model_key=model_key,
            loss_key=loss_key,
            seed=int(seed),
        )

        completed_ok, _, _ = self.validate_completed_seed_artifacts(paths)
        if completed_ok:
            return "completed"
        if paths["failed_marker"].exists():
            return "failed_last_attempt"
        if paths["interrupted_marker"].exists():
            return "interrupted_last_attempt"
        if paths["last_ckpt"].exists():
            return "resumable"
        return "pending"

    def build_pending_work_plan(self) -> pd.DataFrame:
        rows = []
        for model_key in self.ctx.run_model_keys:
            for loss_key in self.ctx.loss_keys_by_model[model_key]:
                for seed in self.ctx.benchmark_seeds:
                    rows.append(
                        {
                            "model_key": model_key,
                            "loss_key": loss_key,
                            "seed": int(seed),
                            "state": self.seed_run_state(model_key, loss_key, int(seed)),
                        }
                    )
        return pd.DataFrame(rows)

    def maybe_generate_deferred_heavy_artifacts(
        self,
        cfg: dict[str, Any],
        loss_key: str,
        seed: int,
        variant_dir: Path,
        resources: dict[str, Any] | None = None,
    ) -> None:
        if not self.ctx.generate_heavy_artifacts_after_training:
            return

        model_key = cfg["model_key"]
        paths = self.build_seed_paths(
            variant_dir=variant_dir,
            model_key=model_key,
            loss_key=loss_key,
            seed=int(seed),
        )

        if self.ctx.enable_reliability_diagrams:
            npz_path = paths["seed_dir"] / "test_outputs.npz"
            if npz_path.exists():
                with np.load(npz_path, allow_pickle=False) as data:
                    labels = data["labels"]
                    probs = data["probs"]
                    calibrated_probs = data["calibrated_probs"] if "calibrated_probs" in data.files else None

                save_reliability_diagram_artifacts(
                    probs=probs,
                    labels=labels,
                    csv_path=paths["seed_dir"] / "reliability_uncalibrated.csv",
                    png_path=paths["seed_dir"] / "reliability_uncalibrated.png",
                    n_bins=self.ctx.ece_n_bins,
                    title="Reliability (uncalibrated)",
                )

                if calibrated_probs is not None:
                    save_reliability_diagram_artifacts(
                        probs=calibrated_probs,
                        labels=labels,
                        csv_path=paths["seed_dir"] / "reliability_calibrated.csv",
                        png_path=paths["seed_dir"] / "reliability_calibrated.png",
                        n_bins=self.ctx.ece_n_bins,
                        title="Reliability (calibrated)",
                    )
                    save_csv(
                        top_label_calibration_frame(probs, labels, self.ctx.label_names),
                        paths["seed_dir"] / "top_label_calibration_uncalibrated.csv",
                        index=False,
                    )
                    save_csv(
                        top_label_calibration_frame(calibrated_probs, labels, self.ctx.label_names),
                        paths["seed_dir"] / "top_label_calibration_calibrated.csv",
                        index=False,
                    )

        if not self.ctx.enable_latency_benchmark:
            return

        latency_payload = self._load_valid_latency_summary(paths["latency_summary"])
        if latency_payload is None:
            latency_payload = self._compute_latency_from_best_checkpoint(
                cfg=cfg,
                loss_key=loss_key,
                seed=int(seed),
                variant_dir=variant_dir,
                resources=resources,
            )
            save_json(
                paths["latency_summary"],
                {**latency_payload, "latency_protocol": self.ctx.latency_protocol},
            )

        self._patch_summary_with_latency(paths["summary"], latency_payload)

    def run_confirmatory_model(self, model_key: str) -> pd.DataFrame:
        self._ensure_runtime_state_initialized()

        if model_key not in self.ctx.run_model_keys:
            raise ValueError(
                f"Unknown model_key={model_key}. Expected one of {self.ctx.run_model_keys}"
            )

        cfg = self.ctx.model_registry[model_key]
        model_dir = model_run_dir(self.ctx.run_output_dir, model_key)

        print("\n" + "=" * 112)
        print(
            f"MODEL RUN START | model={model_key} | "
            f"losses={self.ctx.loss_keys_by_model[model_key]} | seeds={self.ctx.benchmark_seeds}"
        )
        print("=" * 112)

        self.write_run_status("running", f"model:{model_key}", current_model=model_key)

        resources = self.prepare_model_resources(cfg)
        self.model_truncation_overview[model_key] = resources["truncation_evidence"]
        save_json(model_dir / "truncation_evidence.json", resources["truncation_evidence"])

        for loss_key in self.ctx.loss_keys_by_model[model_key]:
            variant_dir = loss_variant_dir(model_dir, loss_key)
            print(f"\nLoss variant start | model={model_key} | loss={loss_key}")

            for seed in self.ctx.benchmark_seeds:
                try:
                    self.run_single_seed(
                        cfg=cfg,
                        loss_key=loss_key,
                        seed=int(seed),
                        variant_dir=variant_dir,
                        resources=resources,
                    )
                except KeyboardInterrupt:
                    self.write_run_status("interrupted", f"model:{model_key}", current_model=model_key)
                    raise
                except Exception as exc:
                    failure_payload = {
                        "model_key": model_key,
                        "loss_key": loss_key,
                        "seed": int(seed),
                        "error": str(exc),
                        "timestamp": self.utc_now_iso(),
                    }
                    self.run_failures.append(failure_payload)
                    save_json(self.ctx.run_failure_log_path, self.run_failures)
                    print(
                        f"[seed-failure-isolated] model={model_key} | loss={loss_key} | "
                        f"seed={seed} | error={exc}"
                    )
                    continue

        model_df = self.aggregate_model_from_disk(model_key)
        self.model_run_tables[model_key] = model_df

        completed_seed_runs = self.count_completed_seed_runs()
        completed_models = self.count_completed_models()

        self.write_run_progress(
            stage=f"model:{model_key}",
            completed_models=int(completed_models),
            completed_seeds=int(completed_seed_runs),
            current_model=model_key,
        )
        self.write_run_status(
            "running",
            f"model:{model_key}",
            current_model=model_key,
            completed_models=int(completed_models),
            completed_seeds=int(completed_seed_runs),
        )

        if model_df.empty:
            print(f"MODEL RUN END | model={model_key} | no completed seed runs available")
        else:
            print(f"MODEL RUN END | model={model_key} | completed_rows={len(model_df)}")

        self.write_run_heartbeat(
            "model_completed",
            model_key=model_key,
            completed_rows=int(model_df.shape[0]) if not model_df.empty else 0,
        )
        self.model_resource_cache.pop(model_key, None)
        gc.collect()
        return model_df

    def rebuild_run_aggregates(
        self,
        generate_deferred_heavy_artifacts: bool = False,
    ):
        self._ensure_runtime_state_initialized()

        all_loss_rows = []
        model_rows = []
        completed_model_keys = []

        for model_key in self.ctx.run_model_keys:
            cfg = self.ctx.model_registry[model_key]
            model_dir = model_run_dir(self.ctx.run_output_dir, model_key)

            resources = None
            if (
                generate_deferred_heavy_artifacts
                and self.ctx.generate_heavy_artifacts_after_training
                and self.ctx.enable_latency_benchmark
            ):
                resources = self.prepare_model_resources(cfg)

            if generate_deferred_heavy_artifacts:
                for loss_key in self.ctx.loss_keys_by_model[model_key]:
                    variant_dir = loss_variant_dir(model_dir, loss_key)
                    for seed in self.ctx.benchmark_seeds:
                        paths = self.build_seed_paths(
                            variant_dir=variant_dir,
                            model_key=model_key,
                            loss_key=loss_key,
                            seed=int(seed),
                        )
                        completed_ok, _, _ = self.validate_completed_seed_artifacts(paths)
                        if completed_ok:
                            try:
                                self.maybe_generate_deferred_heavy_artifacts(
                                    cfg=cfg,
                                    loss_key=loss_key,
                                    seed=int(seed),
                                    variant_dir=variant_dir,
                                    resources=resources,
                                )
                            except Exception as exc:
                                self.run_failures.append(
                                    {
                                        "model_key": model_key,
                                        "loss_key": loss_key,
                                        "seed": int(seed),
                                        "stage": "deferred_heavy_artifacts",
                                        "error": str(exc),
                                        "timestamp": self.utc_now_iso(),
                                    }
                                )

            model_df = self.aggregate_model_from_disk(model_key)
            self.model_run_tables[model_key] = model_df
            if model_df.empty:
                continue

            completed_model_keys.append(model_key)
            all_loss_rows.extend(model_df.to_dict(orient="records"))

            sort_cols = [
                col for col in ["test_macro_f1_mean", "val_macro_f1_mean"] if col in model_df.columns
            ]
            if sort_cols:
                model_df = model_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(
                    drop=True
                )
            model_rows.append(model_df.iloc[0].to_dict())

        save_json(self.ctx.run_failure_log_path, self.run_failures)

        all_loss_df = pd.DataFrame(all_loss_rows)
        if not all_loss_df.empty:
            sort_cols = [
                col for col in ["test_macro_f1_mean", "val_macro_f1_mean"] if col in all_loss_df.columns
            ]
            if sort_cols:
                all_loss_df = all_loss_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(
                    drop=True
                )
            save_csv(all_loss_df, self.ctx.run_output_dir / "all_loss_variant_aggregates.csv", index=False)
        if all_loss_df.empty:
            self.write_run_status(
                "failed",
                "final_aggregation",
                failure_reason="no_completed_model_loss_aggregates",
            )
            self.write_run_heartbeat(
                "aggregation_failed",
                failure_reason="no_completed_model_loss_aggregates",
            )
            raise RuntimeError(
                "No completed model/loss aggregates available."
            )

        model_df = pd.DataFrame(model_rows)
        if not model_df.empty:
            sort_cols = [
                col for col in ["test_macro_f1_mean", "val_macro_f1_mean"] if col in model_df.columns
            ]
            if sort_cols:
                model_df = model_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(
                    drop=True
                )
            save_csv(model_df, self.ctx.run_output_dir / "model_benchmark_summary.csv", index=False)

        skipped_model_keys = sorted(set(self.ctx.run_model_keys) - set(completed_model_keys))

        run_manifest = {
            "artifact_schema_version": "final_confirmatory_benchmark.v2",
            "run_contract_version": self.ctx.run_contract.get("contract_version"),
            "run_contract": self.ctx.run_contract,
            "run_contract_sha256": self.ctx.run_contract_sha256,
            "run_kind": self.ctx.run_kind,
            "run_name": self.ctx.run_name,
            "dataset_version": self.ctx.dataset_version,
            "preprocessing_version": self.ctx.preprocessing_version,
            "model_input_hash_policy": self.ctx.model_input_hash_policy,
            "dataset_metadata": self.ctx.dataset_metadata,
            "run_output_dir": str(self.ctx.run_output_dir),
            "text_col": self.ctx.text_col,
            "label_col": self.ctx.label_col,
            "label_names": self.ctx.label_names,
            "seed_list": [int(seed) for seed in self.ctx.benchmark_seeds],
            "n_seeds": int(len(self.ctx.benchmark_seeds)),
            "model_keys": list(self.ctx.run_model_keys),
            "model_contracts": self.ctx.model_contracts,
            "completed_model_keys": sorted(completed_model_keys),
            "skipped_model_keys": skipped_model_keys,
            "loss_keys_by_model": self.ctx.loss_keys_by_model,
            "fixed_loss_key": self.ctx.fixed_loss_key,
            "checkpoint_selection_rule": self.ctx.checkpoint_selection_rule,
            "deterministic_mode": bool(self.ctx.deterministic_mode),
            "resume_if_available": bool(self.ctx.resume_if_available),
            "skip_completed_seeds": bool(self.ctx.skip_completed_seeds),
            "force_rerun_seeds": bool(self.ctx.force_rerun_seeds),
            "split_summaries": self.ctx.split_summaries,
            "split_hygiene_evidence": self.ctx.split_hygiene_evidence,
            "model_truncation_overview": self.model_truncation_overview,
            "analysis_flags": {
                "split_hygiene_recompute": bool(self.ctx.enable_split_hygiene_recompute),
                "truncation_evidence": bool(self.ctx.enable_truncation_evidence),
                "calibration": bool(self.ctx.enable_calibration),
                "threshold_security_artifacts": bool(self.ctx.enable_threshold_security_artifacts),
                "reliability_diagrams": bool(self.ctx.enable_reliability_diagrams),
                "latency_benchmark": bool(self.ctx.enable_latency_benchmark),
                "heavy_artifacts_during_training": bool(
                    self.ctx.generate_heavy_artifacts_during_training
                ),
                "heavy_artifacts_after_training": bool(generate_deferred_heavy_artifacts),
            },
            "failures": self.run_failures,
            "created_at": self.utc_now_iso(),
        }
        save_json(self.ctx.run_output_dir / "run_manifest.json", run_manifest)

        self.write_run_progress(
            stage="final_aggregation",
            completed_models=int(len(completed_model_keys)),
            completed_seeds=int(self.count_completed_seed_runs()),
            skipped_models=skipped_model_keys,
        )
        self.write_run_status(
            "aggregation_completed",
            "final_aggregation",
            completed_models=int(len(completed_model_keys)),
            skipped_models=skipped_model_keys,
        )
        self.write_run_heartbeat(
            "aggregation_completed",
            completed_models=int(len(completed_model_keys)),
            skipped_models=skipped_model_keys,
        )

        return all_loss_df, model_df, run_manifest
