"""
predict_attack - Production inference wrapper for the staged WAF classifier.
Generated from ml_model/evaluate.ipynb.
"""

import json
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

LABEL_NAMES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
NUM_CLASSES = len(LABEL_NAMES)
MAX_SEQ_LEN = 128
LOW_THRESHOLD = 0.50
HIGH_THRESHOLD = 0.80
MODEL_IDS = {
    "minilm": "nreimers/MiniLM-L6-H384-uncased",
    "distilbert": "distilbert-base-uncased",
    "bert-base": "bert-base-uncased",
}


def _discover_latest_run(staging_dir: Path, model_key: str) -> Path:
    candidates = [
        run_dir for run_dir in staging_dir.iterdir()
        if run_dir.is_dir() and run_dir.name.startswith(model_key + "_")
    ]
    if not candidates:
        raise FileNotFoundError(f"No staged run found for {model_key} in {staging_dir}")
    candidates.sort(key=lambda path: path.name, reverse=True)
    return candidates[0]


def _load_temperature(eval_dir: Path, model_key: str) -> float:
    if not eval_dir.exists():
        return 1.0
    for run_dir in sorted([path for path in eval_dir.iterdir() if path.is_dir()], key=lambda path: path.name, reverse=True):
        result_path = run_dir / f"eval_results_{model_key}_calibrated.json"
        if result_path.exists():
            with result_path.open("r", encoding="utf-8") as handle:
                return float(json.load(handle).get("temperature", 1.0))
    return 1.0


def load_model(model_key: str, staging_dir=None, device="cpu"):
    if model_key not in MODEL_IDS:
        raise KeyError(f"Unknown model key: {model_key}")
    if staging_dir is None:
        staging_dir = Path(__file__).resolve().parent.parent / "model_registry" / "staging"
    staging_dir = Path(staging_dir)
    run_dir = _discover_latest_run(staging_dir, model_key)
    ckpt_path = run_dir / f"best_{model_key}_ckpt.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {ckpt_path}")

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_IDS[model_key], num_labels=NUM_CLASSES)
    state = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_IDS[model_key])
    temperature = _load_temperature(staging_dir.parent / "eval", model_key)
    return model, tokenizer, temperature


def predict_attack(text: str, model, tokenizer, device="cpu", temperature: float = 1.0, return_latency: bool = True):
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
    if max_prob < LOW_THRESHOLD:
        tier = "LOW"
    elif max_prob <= HIGH_THRESHOLD:
        tier = "MEDIUM"
    else:
        tier = "HIGH"

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

