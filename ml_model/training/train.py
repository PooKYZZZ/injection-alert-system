"""Script-first entrypoint for the existing confirmatory training workflow.

The implementation reuses the validated runner extracted from the historical
notebook. It does not promote artifacts; promotion remains an explicit export
operation under ``ml_model.export``.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import torch

from ml_model.preprocessing.dataset_io import (
    build_split_hygiene_evidence,
    build_split_summaries,
    encode_labels,
    load_data_splits,
    load_json,
    make_output_dir,
    resolve_data_dir,
    save_csv,
    save_json,
)
from ml_model.training.config import (
    DEFAULT_MODELS,
    TrainingConfig,
    load_training_config,
)
from ml_model.training.confirmatory_runner import (
    ConfirmatoryRunnerContext,
    FinalConfirmatoryRunner,
)
from ml_model.training.device import resolve_device, resolve_precision
from ml_model.training.paths import default_training_output_dir, resolve_project_root

EXPECTED_CLASSES = [
    "Code Injection",
    "Normal",
    "Other Attacks",
    "SQL Injection",
]
DEFAULT_MODEL_KEYS = DEFAULT_MODELS


DEFAULT_MODEL_REGISTRY = {
    "distilbert": {
        "model_key": "distilbert",
        "model_id": "distilbert-base-uncased",
        "architecture": "transformer",
        "experiment_phase": "controlled_backbone_benchmark",
        "learning_rate": 3e-5,
        "per_device_train_batch_size": 64,
        "gradient_accumulation_steps": 2,
        "effective_batch_size": 128,
        "weight_decay": 0.01,
        "dropout_prob": 0.25,
        "num_train_epochs": 4,
        "warmup_ratio": 0.04,
        "max_seq_len": 128,
        "head_hidden_dim": 256,
        "activation": "gelu",
        "focal_gamma": 2.0,
        "eval_batch_multiplier": 2,
    },
    "minilm_l6": {
        "model_key": "minilm_l6",
        "model_id": "nreimers/MiniLM-L6-H384-uncased",
        "architecture": "transformer",
        "experiment_phase": "controlled_backbone_benchmark",
        "learning_rate": 2e-5,
        "per_device_train_batch_size": 128,
        "gradient_accumulation_steps": 1,
        "effective_batch_size": 128,
        "weight_decay": 0.01,
        "dropout_prob": 0.25,
        "num_train_epochs": 4,
        "warmup_ratio": 0.03,
        "max_seq_len": 128,
        "head_hidden_dim": 256,
        "activation": "gelu",
        "focal_gamma": 2.0,
        "eval_batch_multiplier": 2,
    },
    "tinybert_bigru_attn": {
        "model_key": "tinybert_bigru_attn",
        "model_id": "huawei-noah/TinyBERT_General_6L_768D",
        "architecture": "tinybert_bigru_attention",
        "experiment_phase": "architecture_search",
        "learning_rate": 3e-5,
        "per_device_train_batch_size": 64,
        "gradient_accumulation_steps": 2,
        "effective_batch_size": 128,
        "weight_decay": 0.01,
        "dropout_prob": 0.25,
        "num_train_epochs": 4,
        "warmup_ratio": 0.04,
        "max_seq_len": 128,
        "head_hidden_dim": 256,
        "rnn_hidden_dim": 256,
        "rnn_layers": 1,
        "bidirectional": True,
        "attn_dim": 128,
        "activation": "gelu",
        "focal_gamma": 2.0,
        "eval_batch_multiplier": 2,
    },
}


TrainingOptions = TrainingConfig


def _device_for(options: TrainingOptions) -> torch.device:
    return resolve_device(options.device)


def _limit_split(df, label_col: str, limit: int, seed: int):
    """Take a deterministic small sample while retaining every known class."""

    if limit >= len(df):
        return df.copy()
    labels = list(df[label_col].dropna().drop_duplicates())
    if limit < len(labels):
        raise ValueError(
            f"Sample limit {limit} is too small for {len(labels)} classes "
            f"in {label_col}."
        )
    selected = df.groupby(label_col, sort=True, group_keys=False).head(1)
    remaining = df.drop(index=selected.index)
    additional = remaining.head(limit - len(selected))
    return (
        pd.concat([selected, additional])
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )


def _environment_metadata() -> dict[str, object]:
    package_versions: dict[str, str] = {}
    for package in ("torch", "transformers", "pandas", "numpy", "scikit-learn"):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = "unavailable"
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "package_versions": package_versions,
        "executable": sys.executable,
    }


def find_latest_resumable_run_dir(base_dir: Path, run_name: str) -> Path | None:
    """Return the newest matching run directory that contains a last checkpoint."""

    if not base_dir.is_dir():
        return None
    candidates = [
        path
        for path in base_dir.glob(f"{run_name}_*")
        if path.is_dir() and any(path.glob("**/last_*.pt"))
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def build_runner_context(
    options: TrainingOptions,
) -> tuple[FinalConfirmatoryRunner, Path, dict]:
    explicit_output_dir = options.output_dir is not None
    options = options.validate().resolve_paths()
    unknown_models = sorted(set(options.models) - set(DEFAULT_MODEL_REGISTRY))
    if unknown_models:
        raise ValueError(f"Unknown model keys: {unknown_models}")
    if not options.seeds:
        raise ValueError("At least one training seed is required")
    if options.epochs < 1:
        raise ValueError("epochs must be positive")
    if options.resume_checkpoint and not options.resume_checkpoint.is_file():
        raise FileNotFoundError(
            f"Configured resume checkpoint does not exist: {options.resume_checkpoint}"
        )

    repository_root = resolve_project_root()
    data_dir = options.data_dir or resolve_data_dir(
        options.dataset_version, project_root=repository_root
    )
    df_train, df_val, df_test = load_data_splits(
        data_dir, "combined_payload", "final_label"
    )
    if options.max_train_samples:
        df_train = _limit_split(
            df_train, "final_label", options.max_train_samples, options.seeds[0]
        )
    if options.max_validation_samples:
        df_val = _limit_split(
            df_val, "final_label", options.max_validation_samples, options.seeds[0] + 1
        )
    if options.max_test_samples:
        df_test = _limit_split(
            df_test, "final_label", options.max_test_samples, options.seeds[0] + 2
        )
    _, label_names = encode_labels(
        df_train=df_train,
        df_val=df_val,
        df_test=df_test,
        label_col="final_label",
        expected_classes=EXPECTED_CLASSES,
    )
    split_summaries = build_split_summaries(df_train, df_val, df_test, "final_label")
    split_hygiene_evidence = build_split_hygiene_evidence(
        data_dir=data_dir,
        split_summaries=split_summaries,
        df_train=df_train,
        df_val=df_val,
        df_test=df_test,
        text_col="combined_payload",
    )

    run_name = (
        f"{options.dataset_version}_final_confirmatory_weighted_ce_"
        f"{len(options.seeds)}seed"
    )
    default_output_base_dir = default_training_output_dir(project_root=repository_root)
    resumable_run_dir = (
        None
        if explicit_output_dir or not options.resume
        else find_latest_resumable_run_dir(default_output_base_dir, run_name)
    )
    run_dir = (
        Path(options.output_dir).expanduser().resolve()
        if explicit_output_dir
        else resumable_run_dir
        or make_output_dir(run_name, base_dir=default_output_base_dir)
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    save_csv(
        df_test[["combined_payload", "final_label"]].reset_index(drop=True),
        run_dir / "evaluated_test_rows.csv",
        index=False,
    )
    device = _device_for(options)
    precision = resolve_precision(options.precision, device)
    resolved_options = replace(
        options,
        data_dir=data_dir,
        output_dir=run_dir,
        device=str(device),
        precision=precision,
    )
    run_model_registry = {
        key: {
            **DEFAULT_MODEL_REGISTRY[key],
            "num_train_epochs": options.epochs,
            **(
                {"per_device_train_batch_size": options.batch_size}
                if options.batch_size
                else {}
            ),
            **(
                {"eval_batch_size": options.eval_batch_size}
                if options.eval_batch_size
                else {}
            ),
            **(
                {"learning_rate": options.learning_rate}
                if options.learning_rate
                else {}
            ),
            **({"max_seq_len": options.max_seq_len} if options.max_seq_len else {}),
            **(
                {"gradient_accumulation_steps": options.gradient_accumulation_steps}
                if options.gradient_accumulation_steps
                else {}
            ),
        }
        for key in options.models
    }
    run_kind = "final_confirmatory_benchmark"
    context = ConfirmatoryRunnerContext(
        df_train=df_train,
        df_val=df_val,
        df_test=df_test,
        text_col="combined_payload",
        label_col="final_label",
        label_names=list(label_names),
        num_classes=len(label_names),
        dataset_version=options.dataset_version,
        run_kind=run_kind,
        run_name=run_name,
        run_output_dir=run_dir,
        run_status_path=run_dir / "run_status.json",
        run_progress_path=run_dir / "run_progress.json",
        run_heartbeat_path=run_dir / "run_heartbeat.jsonl",
        run_failure_log_path=run_dir / "run_failures.json",
        model_registry=run_model_registry,
        run_model_keys=list(options.models),
        benchmark_seeds=list(options.seeds),
        loss_keys_by_model={key: ["weighted_ce"] for key in options.models},
        fixed_loss_key="weighted_ce",
        checkpoint_selection_rule="validation_macro_f1 (tie-break: validation_loss)",
        deterministic_mode=True,
        resume_if_available=options.resume,
        resume_checkpoint=options.resume_checkpoint,
        skip_completed_seeds=True,
        force_rerun_seeds=False,
        allow_partial_aggregation=True,
        n_epochs=options.epochs,
        early_stop_patience=2,
        max_grad_norm=1.0,
        log_every_steps=200,
        heartbeat_every_steps=200,
        ece_n_bins=15,
        confidence_thresholds=[0.5, 0.7, 0.8, 0.9],
        dataloader_num_workers=options.num_workers,
        checkpoint_interval_epochs=options.checkpoint_interval_epochs,
        dataloader_prefetch_factor=2,
        enable_split_hygiene_recompute=False,
        enable_truncation_evidence=False,
        enable_calibration=True,
        enable_threshold_security_artifacts=True,
        enable_reliability_diagrams=True,
        enable_latency_benchmark=True,
        generate_heavy_artifacts_during_training=False,
        generate_heavy_artifacts_after_training=True,
        latency_protocol={"batch_size": 1, "warmup_steps": 20, "measure_steps": 200},
        split_summaries=split_summaries,
        split_hygiene_evidence=split_hygiene_evidence,
        device=device,
        cuda_fp16=precision == "fp16",
        cuda_bf16=precision == "bf16",
    )
    runner = FinalConfirmatoryRunner(context)
    bootstrap = {
        "run_kind": run_kind,
        "run_name": run_name,
        "dataset_version": options.dataset_version,
        "data_dir": str(data_dir),
        "run_output_dir": str(run_dir),
        "text_col": context.text_col,
        "label_col": context.label_col,
        "label_names": context.label_names,
        "num_classes": context.num_classes,
        "seed_list": list(options.seeds),
        "model_keys": list(options.models),
        "checkpoint_selection_rule": context.checkpoint_selection_rule,
        "split_summaries": split_summaries,
        "split_hygiene_evidence": context.split_hygiene_evidence,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repository_root),
        "resolved_config": resolved_options.to_dict(),
        "device": str(device),
        "precision": precision,
        "environment": _environment_metadata(),
    }
    return runner, run_dir, bootstrap


def run_training(options: TrainingOptions) -> Path:
    runner, run_dir, bootstrap = build_runner_context(options)
    save_json(run_dir / "run_bootstrap.json", bootstrap)
    runner.set_runtime_state(
        run_failures=(
            load_json(runner.ctx.run_failure_log_path)
            if runner.ctx.run_failure_log_path.exists()
            else []
        ),
        model_run_tables={},
        model_truncation_overview={},
    )
    runner.seed_everything(options.seeds[0], deterministic=True)
    pending = runner.build_pending_work_plan()
    save_csv(pending, run_dir / "pending_work_plan.csv", index=False)
    if options.prepare_only:
        runner.write_run_status("ready", "run_state_planner")
        return run_dir

    for model_key in options.models:
        runner.run_confirmatory_model(model_key)
    runner.rebuild_run_aggregates(generate_deferred_heavy_artifacts=True)
    return run_dir


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="TOML training configuration")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Use the CPU-safe minimal preparation profile",
    )
    parser.add_argument("--dataset-version")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--models", nargs="+", choices=sorted(DEFAULT_MODEL_REGISTRY))
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"))
    parser.add_argument("--precision", choices=("auto", "full", "fp16", "bf16"))
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--eval-batch-size", type=int)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--num-workers", type=int)
    parser.add_argument("--checkpoint-interval-epochs", type=int)
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument("--max-test-samples", type=int)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--gradient-accumulation-steps", type=int)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = load_training_config(args.config) if args.config else TrainingConfig()
    if args.smoke:
        config = TrainingConfig.smoke()
    overrides = {
        key: value
        for key, value in {
            "dataset_version": args.dataset_version,
            "data_dir": args.data_dir,
            "models": tuple(args.models) if args.models else None,
            "seeds": tuple(args.seeds) if args.seeds else None,
            "output_dir": args.output_dir,
            "device": args.device,
            "precision": args.precision,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "num_workers": args.num_workers,
            "checkpoint_interval_epochs": args.checkpoint_interval_epochs,
            "resume_checkpoint": args.resume_checkpoint,
            "max_train_samples": args.max_train_samples,
            "max_validation_samples": args.max_validation_samples,
            "max_test_samples": args.max_test_samples,
            "max_seq_len": args.max_seq_len,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "resume": False if args.no_resume else None,
            "prepare_only": True if args.prepare_only else None,
        }.items()
        if value is not None
    }
    config = replace(config, **overrides).validate()
    run_dir = run_training(
        config,
    )
    print(f"Training run directory: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
