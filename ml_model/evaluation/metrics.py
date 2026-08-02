from __future__ import annotations

import re
import traceback
from contextlib import nullcontext
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import quote

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

CONFIDENCE_BANDS = (
    ("LOW", 0.0, 0.5),
    ("MEDIUM", 0.5, 0.8),
    ("HIGH", 0.8, 1.0000001),
)

DEFAULT_ROBUSTNESS_PERTURBATIONS = {
    "url_percent_encoding": "Percent-encode the full payload.",
    "case_changes": "Toggle case across alphabetic characters.",
    "whitespace_injection": "Inject excessive whitespace and tabs.",
    "comment_injection": "Inject SQL-style comments around high-risk tokens.",
    "fragmentation_style": "Fragment common SQL keywords using separators.",
    "normalization_edges": "Apply normalization-edge substitutions.",
}


def _png_error_artifact_path(png_path: Path) -> Path:
    return png_path.with_name(f"{png_path.stem}_png_error.txt")


def _write_png_error_artifact(png_path: Path, context: str, exc: Exception) -> Path:
    error_path = _png_error_artifact_path(png_path)
    payload = [
        f"png_context: {context}",
        f"png_target: {png_path}",
        f"error_type: {type(exc).__name__}",
        f"error_message: {exc}",
        "",
        "traceback:",
        traceback.format_exc(),
    ]
    error_path.write_text("\n".join(payload), encoding="utf-8")
    return error_path


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lower, upper in zip(bin_edges[:-1], bin_edges[1:]):
        if upper == 1.0:
            in_bin = (confidences >= lower) & (confidences <= upper)
        else:
            in_bin = (confidences >= lower) & (confidences < upper)
        if not np.any(in_bin):
            continue
        bin_acc = accuracies[in_bin].mean()
        bin_conf = confidences[in_bin].mean()
        ece += np.abs(bin_acc - bin_conf) * in_bin.mean()
    return float(ece)


def softmax_np(logits: np.ndarray) -> np.ndarray:
    logits = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def negative_log_likelihood_from_logits(logits: np.ndarray, labels: np.ndarray) -> float:
    logits_t = torch.tensor(logits, dtype=torch.float64)
    labels_t = torch.tensor(labels, dtype=torch.long)
    log_probs = torch.log_softmax(logits_t, dim=1)
    idx = torch.arange(labels_t.shape[0], device=labels_t.device)
    nll = -(log_probs[idx, labels_t]).mean()
    return float(nll.item())


def multiclass_brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    probs_arr = np.asarray(probs, dtype=np.float64)
    labels_arr = np.asarray(labels, dtype=np.int64)
    if probs_arr.ndim != 2:
        raise ValueError(f"Expected probs to be 2D, got shape={probs_arr.shape}")
    if labels_arr.ndim != 1:
        raise ValueError(f"Expected labels to be 1D, got shape={labels_arr.shape}")
    if probs_arr.shape[0] != labels_arr.shape[0]:
        raise ValueError(
            "Mismatched number of rows between probs and labels: "
            f"{probs_arr.shape[0]} vs {labels_arr.shape[0]}"
        )

    n_classes = probs_arr.shape[1]
    one_hot = np.zeros_like(probs_arr, dtype=np.float64)
    one_hot[np.arange(labels_arr.shape[0]), labels_arr] = 1.0
    return float(np.mean(np.sum((probs_arr - one_hot) ** 2, axis=1)))


def mean_std_ci95(values: Sequence[float]) -> dict[str, float | int]:
    arr = np.asarray(list(values), dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return {
            "n": 0,
            "mean": np.nan,
            "std": np.nan,
            "ci95_lower": np.nan,
            "ci95_upper": np.nan,
        }

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    half_width = 1.96 * (std / np.sqrt(max(n, 1))) if n > 1 else 0.0
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "ci95_lower": float(mean - half_width),
        "ci95_upper": float(mean + half_width),
    }


def append_summary_stats(prefix: str, values: Sequence[float]) -> dict[str, float | int]:
    stats = mean_std_ci95(values)
    return {
        f"{prefix}_mean": stats["mean"],
        f"{prefix}_std": stats["std"],
        f"{prefix}_ci95_lower": stats["ci95_lower"],
        f"{prefix}_ci95_upper": stats["ci95_upper"],
    }


def aggregate_numeric_columns(df: pd.DataFrame, exclude: Sequence[str]) -> dict[str, float | int]:
    excluded = set(exclude)
    summary: dict[str, float | int] = {}
    for column in df.columns:
        if column in excluded:
            continue
        if not pd.api.types.is_numeric_dtype(df[column]):
            continue
        values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=np.float64)
        if values.size == 0:
            continue
        summary.update(append_summary_stats(column, values))
    return summary


def aggregate_per_class_metrics(seed_rows: list[pd.DataFrame]) -> pd.DataFrame:
    if not seed_rows:
        return pd.DataFrame(
            columns=[
                "label_id",
                "label_name",
                "precision_mean",
                "precision_std",
                "precision_ci95_lower",
                "precision_ci95_upper",
                "recall_mean",
                "recall_std",
                "recall_ci95_lower",
                "recall_ci95_upper",
                "f1_mean",
                "f1_std",
                "f1_ci95_lower",
                "f1_ci95_upper",
                "support_mean",
                "support_std",
            ]
        )

    base = pd.concat(seed_rows, ignore_index=True)
    required_cols = {"label_id", "label_name", "precision", "recall", "f1", "support"}
    missing_cols = sorted(required_cols - set(base.columns))
    if missing_cols:
        raise ValueError(f"Missing required per-class columns for aggregation: {missing_cols}")

    rows: list[dict[str, float | int | str]] = []
    grouped = base.groupby(["label_id", "label_name"], as_index=False)
    for _, group in grouped:
        label_id = int(group["label_id"].iloc[0])
        label_name = str(group["label_name"].iloc[0])

        precision_stats = mean_std_ci95(pd.to_numeric(group["precision"], errors="coerce").to_numpy(dtype=np.float64))
        recall_stats = mean_std_ci95(pd.to_numeric(group["recall"], errors="coerce").to_numpy(dtype=np.float64))
        f1_stats = mean_std_ci95(pd.to_numeric(group["f1"], errors="coerce").to_numpy(dtype=np.float64))
        support_values = pd.to_numeric(group["support"], errors="coerce").to_numpy(dtype=np.float64)

        rows.append(
            {
                "label_id": label_id,
                "label_name": label_name,
                "precision_mean": precision_stats["mean"],
                "precision_std": precision_stats["std"],
                "precision_ci95_lower": precision_stats["ci95_lower"],
                "precision_ci95_upper": precision_stats["ci95_upper"],
                "recall_mean": recall_stats["mean"],
                "recall_std": recall_stats["std"],
                "recall_ci95_lower": recall_stats["ci95_lower"],
                "recall_ci95_upper": recall_stats["ci95_upper"],
                "f1_mean": f1_stats["mean"],
                "f1_std": f1_stats["std"],
                "f1_ci95_lower": f1_stats["ci95_lower"],
                "f1_ci95_upper": f1_stats["ci95_upper"],
                "support_mean": float(np.mean(support_values)) if support_values.size else np.nan,
                "support_std": float(np.std(support_values, ddof=1)) if support_values.size > 1 else 0.0,
            }
        )

    result = pd.DataFrame(rows)
    return result.sort_values(by=["label_id", "label_name"]).reset_index(drop=True)


def calibration_bins_frame(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> pd.DataFrame:
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)

    rows = []
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    for lower, upper in zip(bin_edges[:-1], bin_edges[1:]):
        if upper == 1.0:
            in_bin = (confidences >= lower) & (confidences <= upper)
        else:
            in_bin = (confidences >= lower) & (confidences < upper)

        count = int(np.sum(in_bin))
        if count == 0:
            rows.append(
                {
                    "bin_lower": float(lower),
                    "bin_upper": float(upper),
                    "count": 0,
                    "accuracy": 0.0,
                    "confidence": 0.0,
                    "gap_abs": 0.0,
                }
            )
            continue

        bin_acc = float(accuracies[in_bin].mean())
        bin_conf = float(confidences[in_bin].mean())
        rows.append(
            {
                "bin_lower": float(lower),
                "bin_upper": float(upper),
                "count": count,
                "accuracy": bin_acc,
                "confidence": bin_conf,
                "gap_abs": float(abs(bin_acc - bin_conf)),
            }
        )

    return pd.DataFrame(rows)


def save_reliability_diagram_artifacts(
    probs: np.ndarray,
    labels: np.ndarray,
    csv_path: Path,
    png_path: Path | None = None,
    n_bins: int = 15,
    title: str | None = None,
) -> pd.DataFrame:
    frame = calibration_bins_frame(probs, labels, n_bins=n_bins)
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    if png_path is not None:
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1.2, label="Perfect calibration")
            ax.plot(frame["confidence"], frame["accuracy"], marker="o", linewidth=1.6, label="Observed")
            ax.set_xlabel("Confidence")
            ax.set_ylabel("Accuracy")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.grid(alpha=0.25)
            if title:
                ax.set_title(title)
            ax.legend(loc="lower right")
            fig.tight_layout()
            fig.savefig(str(png_path), dpi=200)
            plt.close(fig)
        except Exception as exc:
            _write_png_error_artifact(png_path, "reliability_diagram", exc)

    return frame


def top_label_calibration_frame(probs: np.ndarray, labels: np.ndarray, label_names: Sequence[str]) -> pd.DataFrame:
    preds = probs.argmax(axis=1)
    confidences = probs.max(axis=1)
    rows = []

    for label_id, label_name in enumerate(label_names):
        predicted_mask = preds == label_id
        count = int(np.sum(predicted_mask))
        if count == 0:
            rows.append(
                {
                    "label_id": int(label_id),
                    "label_name": str(label_name),
                    "predicted_count": 0,
                    "accuracy": 0.0,
                    "mean_confidence": 0.0,
                    "gap_abs": 0.0,
                }
            )
            continue

        acc = float(np.mean(labels[predicted_mask] == preds[predicted_mask]))
        conf = float(np.mean(confidences[predicted_mask]))
        rows.append(
            {
                "label_id": int(label_id),
                "label_name": str(label_name),
                "predicted_count": count,
                "accuracy": acc,
                "mean_confidence": conf,
                "gap_abs": float(abs(acc - conf)),
            }
        )

    return pd.DataFrame(rows)


def evaluate_from_logits(logits: np.ndarray, labels: np.ndarray, n_bins: int = 15):
    probs = softmax_np(logits)
    preds = probs.argmax(axis=1)
    acc = accuracy_score(labels, preds)
    balanced_acc = balanced_accuracy_score(labels, preds)
    _, macro_recall, _, _ = precision_recall_fscore_support(
        labels,
        preds,
        average="macro",
        zero_division=0,
    )
    macro_f1 = f1_score(labels, preds, average="macro")
    weighted_f1 = f1_score(labels, preds, average="weighted")
    ece = expected_calibration_error(probs, labels, n_bins=n_bins)
    nll = negative_log_likelihood_from_logits(logits, labels)
    brier = multiclass_brier_score(probs, labels)
    return {
        "accuracy": float(acc),
        "balanced_accuracy": float(balanced_acc),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "ece": float(ece),
        "nll": float(nll),
        "brier_score": float(brier),
        "preds": preds,
        "probs": probs,
    }


@torch.no_grad()
def collect_logits_labels_loss(
    model,
    dataloader,
    criterion,
    device: torch.device,
    autocast_context_fn: Callable[[], Any] | None = None,
):
    model.eval()
    total_loss = 0.0
    total_count = 0
    logits_list = []
    labels_list = []

    if autocast_context_fn is None:
        autocast_context_fn = nullcontext

    non_blocking = device.type == "cuda"

    for batch in dataloader:
        ids = batch["input_ids"].to(device, non_blocking=non_blocking)
        mask = batch["attention_mask"].to(device, non_blocking=non_blocking)
        labels = batch["labels"].to(device, non_blocking=non_blocking)

        with autocast_context_fn():
            out = model(input_ids=ids, attention_mask=mask)
            logits = out["logits"]
            loss = criterion(logits, labels)

        logits_list.append(logits.float().cpu().numpy())
        labels_list.append(labels.cpu().numpy())
        total_loss += float(loss.item()) * labels.size(0)
        total_count += labels.size(0)

    logits_np = np.concatenate(logits_list, axis=0)
    labels_np = np.concatenate(labels_list, axis=0)
    return total_loss / max(total_count, 1), logits_np, labels_np


@torch.no_grad()
def collect_logits_from_texts(
    model,
    tokenizer,
    texts: Sequence[str],
    device: torch.device,
    max_len: int,
    batch_size: int = 64,
    autocast_context_fn: Callable[[], Any] | None = None,
) -> np.ndarray:
    model.eval()
    if autocast_context_fn is None:
        autocast_context_fn = nullcontext

    all_logits = []
    for start in range(0, len(texts), batch_size):
        batch_texts = [str(text) for text in texts[start : start + batch_size]]
        encoded = tokenizer(
            batch_texts,
            truncation=True,
            max_length=max_len,
            padding=True,
            return_attention_mask=True,
            return_tensors="pt",
        )
        ids = encoded["input_ids"].to(device)
        mask = encoded["attention_mask"].to(device)

        with autocast_context_fn():
            logits = model(input_ids=ids, attention_mask=mask)["logits"]
        all_logits.append(logits.float().cpu().numpy())

    return np.concatenate(all_logits, axis=0) if all_logits else np.empty((0, 0), dtype=np.float32)


class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits):
        return logits / self.temperature.clamp(min=1e-3)


def fit_temperature_scaling(
    val_logits: np.ndarray,
    val_labels: np.ndarray,
    device: torch.device,
) -> float:
    logits_t = torch.tensor(val_logits, dtype=torch.float32, device=device)
    labels_t = torch.tensor(val_labels, dtype=torch.long, device=device)
    scaler = TemperatureScaler().to(device)
    optimizer = torch.optim.LBFGS([scaler.temperature], lr=0.01, max_iter=50)
    criterion = nn.CrossEntropyLoss()

    def closure():
        optimizer.zero_grad()
        loss = criterion(scaler(logits_t), labels_t)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(scaler.temperature.detach().cpu().item())


def compute_per_class_metrics(
    labels: np.ndarray,
    preds: np.ndarray,
    label_names: list[str],
) -> list[dict[str, float | int | str]]:
    label_ids = np.arange(len(label_names), dtype=np.int64)
    precision, recall, f1, support = precision_recall_fscore_support(
        labels,
        preds,
        labels=label_ids,
        zero_division=0,
    )
    precision_arr = np.asarray(precision, dtype=np.float64)
    recall_arr = np.asarray(recall, dtype=np.float64)
    f1_arr = np.asarray(f1, dtype=np.float64)
    support_arr = np.asarray(support, dtype=np.int64)
    rows: list[dict[str, float | int | str]] = []
    for idx, label_name in enumerate(label_names):
        rows.append(
            {
                "label_id": int(idx),
                "label_name": label_name,
                "precision": float(precision_arr[idx]),
                "recall": float(recall_arr[idx]),
                "f1": float(f1_arr[idx]),
                "support": int(support_arr[idx]),
            }
        )
    return rows


def confusion_matrix_frame(
    labels: np.ndarray,
    preds: np.ndarray,
    label_names: list[str],
) -> pd.DataFrame:
    label_ids = np.arange(len(label_names), dtype=np.int64)
    cm = confusion_matrix(labels, preds, labels=label_ids)
    return pd.DataFrame(cm, index=label_names, columns=label_names)


def save_confusion_matrix_artifacts(
    labels: np.ndarray,
    preds: np.ndarray,
    label_names: list[str],
    csv_path: Path,
    png_path: Path | None = None,
    title: str | None = None,
) -> pd.DataFrame:
    cm_df = confusion_matrix_frame(labels, preds, label_names)
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    cm_df.to_csv(csv_path)

    if png_path is not None:
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 6))
            plotted = False
            try:
                import seaborn as sns

                sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
                plotted = True
            except Exception:
                pass

            if not plotted:
                cm_values = np.asarray(cm_df.values, dtype=np.float64)
                im = ax.imshow(cm_values, cmap="Blues")
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                ax.set_xticks(range(len(label_names)), label_names, rotation=45, ha="right")
                ax.set_yticks(range(len(label_names)), label_names)
                for i in range(cm_df.shape[0]):
                    for j in range(cm_df.shape[1]):
                        value = int(cm_values[i, j])
                        ax.text(j, i, str(value), ha="center", va="center", color="black")

            ax.set_xlabel("Predicted label")
            ax.set_ylabel("True label")
            if title:
                ax.set_title(title)
            fig.tight_layout()
            fig.savefig(str(png_path), dpi=200)
            plt.close(fig)
        except Exception as exc:
            _write_png_error_artifact(png_path, "confusion_matrix", exc)

    return cm_df


def attack_to_normal_false_negative_frame(
    labels: np.ndarray,
    preds: np.ndarray,
    label_names: list[str],
    normal_label: str = "Normal",
) -> pd.DataFrame:
    if normal_label not in label_names:
        raise ValueError(f"Normal label '{normal_label}' not found in label names: {label_names}")

    normal_idx = label_names.index(normal_label)
    rows = []
    for idx, label_name in enumerate(label_names):
        if idx == normal_idx:
            continue
        total = int(np.sum(labels == idx))
        missed_as_normal = int(np.sum((labels == idx) & (preds == normal_idx)))
        rate = float(missed_as_normal / total) if total > 0 else 0.0
        rows.append(
            {
                "attack_label": label_name,
                "attack_label_id": int(idx),
                "total_true_samples": total,
                "predicted_as_normal": missed_as_normal,
                "false_negative_rate_to_normal": rate,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(by="false_negative_rate_to_normal", ascending=False).reset_index(drop=True)


def normal_false_positive_metrics(
    labels: np.ndarray,
    preds: np.ndarray,
    label_names: Sequence[str],
    normal_label: str = "Normal",
) -> dict[str, float | int]:
    if normal_label not in label_names:
        raise ValueError(f"Normal label '{normal_label}' not found in label names: {label_names}")
    normal_idx = list(label_names).index(normal_label)
    normal_mask = labels == normal_idx
    total = int(np.sum(normal_mask))
    predicted_attack = int(np.sum(normal_mask & (preds != normal_idx)))
    return {
        "normal_total": total,
        "normal_predicted_attack": predicted_attack,
        "normal_false_positive_rate": float(predicted_attack / total) if total > 0 else 0.0,
    }


def confidence_band_summary_frame(
    labels: np.ndarray,
    preds: np.ndarray,
    probs: np.ndarray,
    bands: Sequence[tuple[str, float, float]] = CONFIDENCE_BANDS,
) -> pd.DataFrame:
    confidences = probs.max(axis=1)
    rows: list[dict[str, float | int | str]] = []
    total_count = max(int(labels.shape[0]), 1)

    for band_name, lower, upper in bands:
        if upper >= 1.0:
            mask = (confidences >= lower) & (confidences <= upper)
        else:
            mask = (confidences >= lower) & (confidences < upper)

        count = int(np.sum(mask))
        coverage = float(count / total_count)
        if count == 0:
            rows.append(
                {
                    "band": band_name,
                    "lower": float(lower),
                    "upper": float(upper),
                    "count": 0,
                    "coverage": coverage,
                    "accuracy": 0.0,
                    "macro_precision": 0.0,
                    "macro_recall": 0.0,
                    "macro_f1": 0.0,
                }
            )
            continue

        y_true = labels[mask]
        y_pred = preds[mask]
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            average="macro",
            zero_division=0,
        )
        rows.append(
            {
                "band": band_name,
                "lower": float(lower),
                "upper": float(upper),
                "count": count,
                "coverage": coverage,
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "macro_precision": float(precision),
                "macro_recall": float(recall),
                "macro_f1": float(f1),
            }
        )

    return pd.DataFrame(rows)


def per_class_recall_at_threshold_frame(
    labels: np.ndarray,
    preds: np.ndarray,
    probs: np.ndarray,
    label_names: Sequence[str],
    thresholds: Iterable[float] = (0.5, 0.7, 0.8, 0.9),
) -> pd.DataFrame:
    confidences = probs.max(axis=1)
    rows = []
    for threshold in thresholds:
        accepted = confidences >= float(threshold)
        for label_id, label_name in enumerate(label_names):
            true_mask = labels == label_id
            total = int(np.sum(true_mask))
            correct_and_kept = int(np.sum(true_mask & (preds == label_id) & accepted))
            recall = float(correct_and_kept / total) if total > 0 else 0.0
            rows.append(
                {
                    "threshold": float(threshold),
                    "label_id": int(label_id),
                    "label_name": str(label_name),
                    "total_true": total,
                    "correct_and_confident": correct_and_kept,
                    "recall": recall,
                }
            )
    return pd.DataFrame(rows)


def threshold_security_summary(
    labels: np.ndarray,
    preds: np.ndarray,
    probs: np.ndarray,
    label_names: Sequence[str],
    normal_label: str = "Normal",
) -> dict[str, Any]:
    normal_metrics = normal_false_positive_metrics(labels, preds, label_names, normal_label=normal_label)
    attack_to_normal_df = attack_to_normal_false_negative_frame(
        labels,
        preds,
        list(label_names),
        normal_label=normal_label,
    )
    attack_total = int(attack_to_normal_df["total_true_samples"].sum()) if not attack_to_normal_df.empty else 0
    attack_escaped = int(attack_to_normal_df["predicted_as_normal"].sum()) if not attack_to_normal_df.empty else 0

    return {
        "normal_false_positive": normal_metrics,
        "attack_escape_total": {
            "attack_total": attack_total,
            "predicted_as_normal": attack_escaped,
            "attack_escape_rate": float(attack_escaped / attack_total) if attack_total > 0 else 0.0,
        },
        "attack_to_normal_by_class": attack_to_normal_df,
        "confidence_band_summary": confidence_band_summary_frame(labels, preds, probs),
        "per_class_recall_at_threshold": per_class_recall_at_threshold_frame(labels, preds, probs, label_names),
    }


def model_size_megabytes(model: nn.Module) -> float:
    n_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    return float(n_bytes / (1024 * 1024))


@torch.no_grad()
def estimate_inference_latency_ms(
    model: nn.Module,
    sample_batch: dict[str, torch.Tensor],
    device: torch.device,
    warmup_steps: int = 3,
    measure_steps: int = 10,
    autocast_context_fn: Callable[[], Any] | None = None,
) -> float:
    if autocast_context_fn is None:
        autocast_context_fn = nullcontext

    model.eval()
    ids = sample_batch["input_ids"].to(device)
    mask = sample_batch["attention_mask"].to(device)

    for _ in range(warmup_steps):
        with autocast_context_fn():
            _ = model(input_ids=ids, attention_mask=mask)
    if device.type == "cuda":
        torch.cuda.synchronize()

    t0 = perf_counter()
    for _ in range(measure_steps):
        with autocast_context_fn():
            _ = model(input_ids=ids, attention_mask=mask)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = perf_counter() - t0

    return float((elapsed / max(measure_steps, 1)) * 1000.0)


@torch.no_grad()
def benchmark_inference_latency(
    model: nn.Module,
    sample_batch: dict[str, torch.Tensor],
    device: torch.device,
    warmup_steps: int = 20,
    measure_steps: int = 200,
    autocast_context_fn: Callable[[], Any] | None = None,
) -> dict[str, float | int | str | bool]:
    if autocast_context_fn is None:
        autocast_context_fn = nullcontext

    model.eval()
    ids = sample_batch["input_ids"].to(device)
    mask = sample_batch["attention_mask"].to(device)

    autocast_bf16 = bool(
        device.type == "cuda"
        and autocast_context_fn is not nullcontext
        and hasattr(torch.cuda, "is_bf16_supported")
        and torch.cuda.is_bf16_supported()
    )

    batch_size = int(ids.shape[0]) if ids.ndim >= 1 else 1
    sequence_length = int(ids.shape[1]) if ids.ndim >= 2 else 0

    for _ in range(max(int(warmup_steps), 0)):
        with autocast_context_fn():
            _ = model(input_ids=ids, attention_mask=mask)
    if device.type == "cuda":
        torch.cuda.synchronize()

    timings_ms: list[float] = []
    for _ in range(max(int(measure_steps), 1)):
        t0 = perf_counter()
        with autocast_context_fn():
            _ = model(input_ids=ids, attention_mask=mask)
        if device.type == "cuda":
            torch.cuda.synchronize()
        timings_ms.append(float((perf_counter() - t0) * 1000.0))

    timing_arr = np.asarray(timings_ms, dtype=np.float64)
    return {
        "latency_mean_ms": float(np.mean(timing_arr)),
        "latency_std_ms": float(np.std(timing_arr, ddof=1)) if timing_arr.size > 1 else 0.0,
        "latency_p50_ms": float(np.percentile(timing_arr, 50)),
        "latency_p95_ms": float(np.percentile(timing_arr, 95)),
        "latency_min_ms": float(np.min(timing_arr)),
        "latency_max_ms": float(np.max(timing_arr)),
        "n_measurements": int(timing_arr.size),
        "batch_size": int(batch_size),
        "sequence_length": int(sequence_length),
        "device": str(device),
        "autocast_bf16": autocast_bf16,
    }


def apply_text_perturbation(text: str, perturbation_key: str) -> str:
    payload = str(text)
    key = perturbation_key.lower().strip()

    if key == "url_percent_encoding":
        return quote(payload, safe="")

    if key == "case_changes":
        out = []
        for idx, ch in enumerate(payload):
            if ch.isalpha():
                out.append(ch.upper() if idx % 2 == 0 else ch.lower())
            else:
                out.append(ch)
        return "".join(out)

    if key == "whitespace_injection":
        return re.sub(r"\s+", "  \t  ", payload)

    if key == "comment_injection":
        token_pattern = re.compile(r"(?i)\b(select|union|where|from|or|and|drop|insert|delete|update)\b")
        return token_pattern.sub(lambda m: f"/**/{m.group(0)}/**/", payload)

    if key == "fragmentation_style":
        token_pattern = re.compile(r"(?i)\b(select|union|where|from|or|and|drop|insert|delete|update)\b")

        def _fragment(match: re.Match[str]) -> str:
            token = match.group(0)
            return "/*/".join(list(token))

        return token_pattern.sub(_fragment, payload)

    if key == "normalization_edges":
        normalized = payload.replace("+", " ")
        normalized = normalized.replace("%2F", "/").replace("%2f", "/")
        normalized = normalized.replace("\\", "/")
        normalized = normalized.replace("%27", "'").replace("%22", '"')
        return normalized.strip()

    raise ValueError(f"Unknown perturbation key: {perturbation_key}")


def apply_perturbation_batch(texts: Sequence[str], perturbation_key: str) -> list[str]:
    return [apply_text_perturbation(text, perturbation_key) for text in texts]


def robustness_retention_row(
    labels: np.ndarray,
    baseline_preds: np.ndarray,
    perturbed_preds: np.ndarray,
    perturbation_key: str,
) -> dict[str, float | str]:
    baseline_acc = float(accuracy_score(labels, baseline_preds))
    baseline_macro_f1 = float(f1_score(labels, baseline_preds, average="macro"))
    perturbed_acc = float(accuracy_score(labels, perturbed_preds))
    perturbed_macro_f1 = float(f1_score(labels, perturbed_preds, average="macro"))

    return {
        "perturbation": perturbation_key,
        "baseline_accuracy": baseline_acc,
        "perturbed_accuracy": perturbed_acc,
        "accuracy_drop": float(baseline_acc - perturbed_acc),
        "accuracy_retention": float(perturbed_acc / baseline_acc) if baseline_acc > 0 else 0.0,
        "baseline_macro_f1": baseline_macro_f1,
        "perturbed_macro_f1": perturbed_macro_f1,
        "macro_f1_drop": float(baseline_macro_f1 - perturbed_macro_f1),
        "macro_f1_retention": float(perturbed_macro_f1 / baseline_macro_f1) if baseline_macro_f1 > 0 else 0.0,
    }


def robustness_failure_examples_frame(
    original_texts: Sequence[str],
    perturbed_texts: Sequence[str],
    labels: np.ndarray,
    baseline_preds: np.ndarray,
    perturbed_preds: np.ndarray,
    label_names: Sequence[str],
    perturbation_key: str,
    max_examples: int = 25,
) -> pd.DataFrame:
    examples = []
    for idx, (orig, perturbed) in enumerate(zip(original_texts, perturbed_texts)):
        base_ok = baseline_preds[idx] == labels[idx]
        perturbed_failed = perturbed_preds[idx] != labels[idx]
        if not (base_ok and perturbed_failed):
            continue
        examples.append(
            {
                "row_index": int(idx),
                "perturbation": perturbation_key,
                "true_label": label_names[int(labels[idx])],
                "baseline_pred": label_names[int(baseline_preds[idx])],
                "perturbed_pred": label_names[int(perturbed_preds[idx])],
                "original_text": str(orig)[:400],
                "perturbed_text": str(perturbed)[:400],
            }
        )
        if len(examples) >= max_examples:
            break

    return pd.DataFrame(examples)