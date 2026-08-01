"""
predict_attack - Production inference wrapper for the staged WAF classifier.
Historical source: ml_model/notebooks/legacy/evaluate.ipynb.
"""

import json
import logging
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml_model.confidence_tiers import (
    ConfidenceThresholds,
    DEFAULT_CONFIDENCE_THRESHOLDS,
    classify_confidence,
)

logger = logging.getLogger(__name__)

LABEL_NAMES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
NUM_CLASSES = len(LABEL_NAMES)
MAX_SEQ_LEN = 128
MODEL_IDS = {
    "minilm": "nreimers/MiniLM-L6-H384-uncased",
    "distilbert": "distilbert-base-uncased",
    "bert-base": "bert-base-uncased",
}
MANIFEST_NAME = "serving_manifest.json"


def _discover_latest_run(staging_dir: Path, model_key: str) -> Path:
    candidates = [
        run_dir for run_dir in staging_dir.iterdir()
        if run_dir.is_dir() and run_dir.name.startswith(model_key + "_")
    ]
    if not candidates:
        raise FileNotFoundError(f"No staged run found for {model_key} in {staging_dir}")
    candidates.sort(key=lambda path: path.name, reverse=True)
    return candidates[0]


def _resolve_run_dir(staging_dir: Path, model_key: str) -> Path:
    if staging_dir.name.startswith(model_key + "_"):
        return staging_dir
    return _discover_latest_run(staging_dir, model_key)


def _load_model_id(run_dir: Path, model_key: str) -> str:
    config_path = run_dir / "config_used.json"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            model_id = json.load(handle).get("model_id")
        if isinstance(model_id, str) and model_id.strip():
            return model_id.strip()
    return MODEL_IDS[model_key]


def _load_temperature(eval_dir: Path, model_key: str) -> float:
    if not eval_dir.exists():
        return 1.0
    for run_dir in sorted([path for path in eval_dir.iterdir() if path.is_dir()], key=lambda path: path.name, reverse=True):
        result_path = run_dir / f"eval_results_{model_key}_calibrated.json"
        if result_path.exists():
            with result_path.open("r", encoding="utf-8") as handle:
                return float(json.load(handle).get("temperature", 1.0))
    return 1.0


def _load_packaged_manifest_temperature(run_dir: Path) -> float | None:
    manifest_path = run_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return None

    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    try:
        temperature = float(manifest["temperature"])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(
            f"Manifest at {manifest_path!r} has missing or invalid field 'temperature': {e}"
        ) from e

    label_names = manifest.get("label_names")
    if not isinstance(label_names, list) or not all(isinstance(value, str) for value in label_names):
        raise RuntimeError(
            f"Manifest at {manifest_path!r} has missing or invalid field 'label_names': "
            f"expected list[str], got {label_names!r}."
        )
    if label_names != LABEL_NAMES:
        raise RuntimeError(
            f"Manifest at {manifest_path!r}: 'label_names' mismatch. "
            f"Got {label_names!r}, expected {LABEL_NAMES!r}."
        )

    max_seq_len = manifest.get("max_seq_len")
    if not isinstance(max_seq_len, int) or isinstance(max_seq_len, bool):
        raise RuntimeError(
            f"Manifest at {manifest_path!r} has missing or invalid field 'max_seq_len': "
            f"expected int, got {max_seq_len!r}."
        )
    if max_seq_len != MAX_SEQ_LEN:
        raise RuntimeError(
            f"Manifest at {manifest_path!r}: 'max_seq_len' mismatch. "
            f"Got {max_seq_len!r}, expected {MAX_SEQ_LEN!r}."
        )

    return temperature


def load_model(model_key: str, staging_dir=None, device="cpu"):
    if model_key not in MODEL_IDS:
        raise KeyError(f"Unknown model key: {model_key}")
    if staging_dir is None:
        staging_dir = Path(__file__).resolve().parent.parent / "model_registry" / "staging"
    staging_dir = Path(staging_dir)
    run_dir = _resolve_run_dir(staging_dir, model_key)
    ckpt_path = run_dir / f"best_{model_key}_ckpt.pt"
    manifest_temperature = _load_packaged_manifest_temperature(run_dir)
    if manifest_temperature is None:
        temperature = _load_temperature(run_dir.parent.parent / "eval", model_key)
    else:
        temperature = manifest_temperature

    try:
        model = AutoModelForSequenceClassification.from_pretrained(
            run_dir,
            local_files_only=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            run_dir,
            local_files_only=True,
        )
        model.to(device).eval()
        return model, tokenizer, temperature
    except (OSError, ValueError) as exc:
        if not ckpt_path.exists():
            raise RuntimeError(
                f"Failed to load local packaged artifact from '{run_dir}' and no compatibility checkpoint exists"
            ) from exc

        model_id = _load_model_id(run_dir, model_key)
        logger.warning(
            "Falling back to checkpoint-based loading for '%s' from '%s': %s",
            model_key,
            run_dir,
            exc,
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_id,
            num_labels=NUM_CLASSES,
            local_files_only=True,
        )
        state = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
        model.to(device).eval()
        tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
        return model, tokenizer, temperature


def predict_attack(
    text: str,
    model,
    tokenizer,
    device="cpu",
    temperature: float = 1.0,
    return_latency: bool = True,
    confidence_thresholds: ConfidenceThresholds | None = None,
):
    if isinstance(device, str):
        device = torch.device(device)

    start = time.perf_counter()
    encoded = tokenizer(text, truncation=True, max_length=MAX_SEQ_LEN, return_tensors="pt", padding=True)
    encoded = {name: tensor.to(device) for name, tensor in encoded.items()}

    with torch.no_grad():
        logits = model(**encoded).logits.float().cpu()

    probs = torch.softmax(logits / float(temperature), dim=-1).squeeze().tolist()
    pred_idx = int(np.argmax(probs))
    max_prob = float(max(probs))
    tier = classify_confidence(
        max_prob,
        thresholds=confidence_thresholds or DEFAULT_CONFIDENCE_THRESHOLDS,
    )

    payload = {
        "label": LABEL_NAMES[pred_idx],
        "label_idx": pred_idx,
        "probs": [round(float(value), 6) for value in probs],
        "max_prob": round(max_prob, 6),
        "tier": tier,
    }
    if return_latency:
        payload["latency_ms"] = round((time.perf_counter() - start) * 1000.0, 3)
    return payload
