"""Explicit, framework-backed device and precision selection."""

from __future__ import annotations

import torch


def _mps_available() -> bool:
    return bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())


def _cuda_bf16_supported() -> bool:
    if not (
        torch.cuda.is_available()
        and hasattr(torch.cuda, "is_bf16_supported")
    ):
        return False
    try:
        return bool(torch.cuda.is_bf16_supported())
    except Exception:
        return False


def resolve_device(requested: str = "auto") -> torch.device:
    requested = requested.lower().strip()
    if requested not in {"auto", "cpu", "cuda", "mps"}:
        raise ValueError(
            f"Unsupported device '{requested}'. Use auto, cpu, cuda, or mps."
        )

    if requested == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if _mps_available():
            return torch.device("mps")
        return torch.device("cpu")

    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA was requested but is unavailable in this PyTorch installation."
        )
    if requested == "mps" and not _mps_available():
        raise RuntimeError(
            "MPS was requested but is unavailable in this PyTorch installation."
        )

    return torch.device(requested)


def resolve_precision(requested: str, device: torch.device) -> str:
    requested = requested.lower().strip()
    if requested not in {"auto", "full", "fp16", "bf16"}:
        raise ValueError(
            f"Unsupported precision '{requested}'. Use auto, full, fp16, or bf16."
        )

    fp16_supported = bool(device.type == "cuda" and torch.cuda.is_available())
    bf16_supported = bool(device.type == "cuda" and _cuda_bf16_supported())
    if requested == "fp16" and not fp16_supported:
        raise RuntimeError(
            "float16 precision was requested but is supported only on CUDA devices."
        )
    if requested == "bf16" and not bf16_supported:
        raise RuntimeError(
            "bfloat16 precision was requested but is unsupported on this device."
        )
    if requested == "auto":
        if bf16_supported:
            return "bf16"
        if fp16_supported:
            return "fp16"
        return "full"
    return requested
