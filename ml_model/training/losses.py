from __future__ import annotations

from typing import Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

LOSS_ABLATION_GRID = ("ce", "weighted_ce", "focal", "weighted_focal")


def compute_class_weights(
    label_ids: np.ndarray,
    label_names: Sequence[str],
) -> np.ndarray:
    counts = np.bincount(label_ids, minlength=len(label_names)).astype(np.float64)
    counts = np.clip(counts, a_min=1.0, a_max=None)
    weights = counts.sum() / (len(label_names) * counts)
    weights = weights / np.mean(weights)
    return weights.astype(np.float32)


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, alpha: torch.Tensor | None = None):
        super().__init__()
        if alpha is not None:
            self.register_buffer("alpha", alpha)
        else:
            self.alpha = None
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=1)
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = log_pt.exp()
        if self.alpha is None:
            alpha_t = torch.ones_like(pt)
        else:
            alpha_t = self.alpha.gather(0, targets)
        focal_factor = (1.0 - pt).pow(self.gamma)
        loss = -alpha_t * focal_factor * log_pt
        return loss.mean()


def build_loss(
    loss_key: str,
    class_weights: torch.Tensor,
    gamma: float,
) -> tuple[nn.Module, dict[str, float | str | bool | None]]:
    loss_key = loss_key.lower().strip()
    if loss_key not in LOSS_ABLATION_GRID:
        raise ValueError(f"Unsupported loss key '{loss_key}'. Expected one of: {LOSS_ABLATION_GRID}")

    if loss_key == "ce":
        criterion = nn.CrossEntropyLoss()
    elif loss_key == "weighted_ce":
        criterion = nn.CrossEntropyLoss(weight=class_weights)
    elif loss_key == "focal":
        criterion = FocalLoss(gamma=gamma, alpha=None)
    else:
        criterion = FocalLoss(gamma=gamma, alpha=class_weights)

    metadata = {
        "loss_key": loss_key,
        "uses_class_weights": bool(loss_key in {"weighted_ce", "weighted_focal"}),
        "focal_gamma": float(gamma) if "focal" in loss_key else None,
    }
    return criterion, metadata
