# Training Implementation Plan v2.0
## Phase 3 — Transformer Fine-Tuning Pipeline
### Deep Learning-Based Confidence Classification for Context-Aware Injection Alert
**Team 13 | Capstone | Dataset: SRBH_clean_v3.1.0 | Date: 2026-03-11**

---

## Hardware Context

Training runs locally on a **Lenovo Legion R9000P** with the following relevant specs:

| Component | Spec |
|-----------|------|
| GPU | RTX 3060 Laptop, ~140W TGP, **6GB GDDR6 VRAM** |
| CPU | Ryzen 7 6800H, 8C/16T, up to 4.7GHz |
| RAM | 16GB DDR5-4800 dual-channel |
| CUDA | Ampere architecture, 3rd-gen Tensor Cores (FP16 native) |

The 6GB VRAM is the governing constraint for all batch and sequence length decisions in this plan. Everything from per-device batch size to whether gradient checkpointing is needed is derived from this number. Production inference will run on the same machine (CPU-only), so CPU latency measurement requires no separate environment.

---

## Project State This Plan Is Built From

**Dataset:** `SRBH_clean_v3.1.0` — 159,873 train / 19,661 val / 19,505 test, stratified, 0% cross-split leakage. Class distribution: SQL Injection 46.74%, Other Attacks 30.99%, Normal 18.76%, Code Injection 3.51%. Code Injection at 3.51% is the minority class and the one most likely to be harmed by default unweighted loss.

**Architecture:** Three plain fine-tuned transformers — **BERT-base** (~110M params), **DistilBERT** (~66M params), **MiniLM-L6** (~22.7M params) — compared under identical conditions. Classification head is a standard linear layer on `[CLS]` token output via `AutoModelForSequenceClassification`. No CNN. No frozen layers.

**Token stats (Phase 2 confirmed):** p95 = 119 tokens (test split worst case), p99 = 161, median = 46–47 across all splits. `max_seq_len = 128` is the locked baseline.

**Training config baseline (`training_config.yaml`):** AdamW, lr = 2e-5, linear warmup 6%, 5 epochs max, early stop patience = 3 on Macro-F1, FP16, seed 42, class-weighted loss enabled.

**Confidence thresholds (locked, never change):** LOW <50%, MEDIUM 50–80%, HIGH >80%. These drive real enforcement actions — calibrated probabilities are required, not raw softmax.

**Target metrics:** Accuracy ≥95%, Macro-F1 ≥0.85, FPR ≤3%, inference latency <100ms.

---

## Step 1 — Establish a Concrete VRAM Budget Before Writing Any Training Code

Before a single line of `train.py` is written, you need to know what actually fits in 6GB. The VRAM consumed during training has four components: (1) model weights — at FP16 this is roughly 2 bytes per parameter; (2) optimizer states — AdamW stores two momentum terms per parameter at FP32, adding roughly 8 bytes per parameter; (3) gradients — one FP16/FP32 copy per parameter; (4) activations — proportional to batch size × sequence length × hidden dimension, and this is the variable you control via batch size.

For reference: BERT-base at FP16 weighs roughly 440MB in weights alone. AdamW optimizer states add another ~880MB. That leaves approximately 4.5GB for activations, gradients, and CUDA overhead before you hit the 6GB wall. With `max_seq_len=128` and FP16 enabled, a safe starting `per_device_train_batch_size` for BERT-base is **8**, with `gradient_accumulation_steps=16` to reach the effective batch size of 128. For DistilBERT (~264MB weights), a per-device batch size of **16** with accumulation of 8 is feasible. For MiniLM-L6 (~91MB weights), a per-device batch size of **16–32** with accumulation adjusted accordingly is safe. These are starting points — run `nvidia-smi dmon` during the first epoch and adjust downward if VRAM usage exceeds ~5.2GB (leaving headroom for driver overhead).

The key rule for FP16 on Ampere: keep batch sizes as multiples of 8. Tensor Cores on the RTX 3060's Ampere architecture are most efficient when matrix dimensions are divisible by 8. A batch size of 8 is better than 7, and 16 is better than 15. This is not a preference — misaligned dimensions underutilize the hardware measurably.

**Concrete output of this step:** A pre-flight `check_vram.py` script that loads each model checkpoint, runs a single forward+backward pass with the intended batch size and sequence length, prints peak VRAM usage via `torch.cuda.max_memory_allocated()`, and exits. Run this before the full training loop on every model. It takes 30 seconds and prevents wasted multi-hour runs that OOM at step 200.

---

## Step 2 — Use AutoTokenizer Per Model with Offline Caching

Each model must load its own pretrained tokenizer via `AutoTokenizer.from_pretrained(model_name)`. Even though all three backbones share the `bert-base-uncased` vocabulary, their tokenizer configurations differ in ways that matter (DistilBERT drops `token_type_ids` entirely, for example). Hardcoding `DistilBertTokenizer` and then swapping the model to BERT-base is a silent bug — `AutoTokenizer` removes this class of error by tying the tokenizer to the model string in `training_config.yaml`.

Tokenization should be run once as an offline preprocessing step using `dataset.map(batched=True, num_proc=4)` over all three parquet splits and the results saved to disk. The Ryzen 7 6800H has 8 cores, so `num_proc=4` uses half the cores without starving the OS. Cached tokenized datasets mean that re-running experiments (which you will do many times) skips the tokenization step entirely. On 159,873 training rows, offline tokenization takes roughly 2–4 minutes the first time and 0 seconds on every subsequent run.

Store only `input_ids` and `attention_mask`. Drop `token_type_ids` — DistilBERT and MiniLM-L6 do not use them, and carrying extra tensor columns wastes RAM bandwidth during DataLoader iteration on the 16GB DDR5 system.

**Concrete deliverable:** `ml_model/training/data_loader.py` with a `build_tokenizer(model_name)` function and a `build_dataloaders(model_name, max_seq_len, batch_size, cache_dir)` function. The cache directory should be per-model so BERT-base and DistilBERT tokenizations don't overwrite each other.

---

## Step 3 — Apply Dynamic Padding via DataCollatorWithPadding

Padding should happen at the DataLoader collation stage, not at tokenization time. `DataCollatorWithPadding(tokenizer=tokenizer)` pads each batch only to the longest sequence in that batch, not to `max_seq_len` globally. For your dataset, where the median token length is 46–47 across all splits, most batches will be padded to around 60–80 tokens, not 128. This meaningfully reduces the activation memory per batch — a batch padded to 64 tokens uses roughly half the attention memory of the same batch padded to 128 — which directly relaxes the VRAM pressure on the 6GB card.

This is the correct pattern in Hugging Face's own fine-tuning documentation and is strictly better than static global padding for variable-length datasets. There is no argument for global padding here. Pass the collator to both the train and validation `DataLoader` objects.

---

## Step 4 — Enable Gradient Checkpointing for BERT-base

For MiniLM-L6 and DistilBERT, gradient checkpointing is optional — their smaller parameter counts leave enough activation headroom at `per_device_train_batch_size=16`. For BERT-base at 110M parameters, gradient checkpointing is **recommended** on a 6GB card to safely use a per-device batch size larger than 4–8 without risking OOM errors mid-epoch.

Gradient checkpointing works by not storing all intermediate forward-pass activations, instead recomputing them on demand during the backward pass. The tradeoff is roughly 20–30% slower training per epoch in exchange for substantial activation memory savings. For BERT-base, this is a worthwhile trade: it allows a larger per-device batch size, which means fewer gradient accumulation steps, which partially offsets the per-step slowdown. Enable it via `gradient_checkpointing=True` in `TrainingArguments` or via `model.gradient_checkpointing_enable()` before the training loop.

Do not enable gradient checkpointing for MiniLM-L6 or DistilBERT unless the `check_vram.py` pre-flight confirms headroom is genuinely tight. For smaller models, it adds overhead for no practical benefit.

---

## Step 5 — Fix the Batch Configuration Per Model

The `training_config.yaml` default of `per_device_train_batch_size=32` with `gradient_accumulation_steps=4` (effective batch = 128) was written without a specific hardware target. On 6GB VRAM, batch size 32 will OOM on BERT-base and likely DistilBERT. The revised per-model starting configurations are:

| Model | Per-Device Batch | Grad Accum Steps | Effective Batch | Gradient Checkpointing |
|-------|-----------------|-----------------|-----------------|------------------------|
| MiniLM-L6 | 16 | 8 | 128 | No |
| DistilBERT | 16 | 8 | 128 | No (optional) |
| BERT-base | 8 | 16 | 128 | Yes |

All three maintain an effective batch size of 128, which keeps the optimization dynamics comparable across models. The learning rate of 2e-5 and warmup of 6% remain unchanged — these were chosen for full fine-tuning of BERT-family models at this effective batch size and are valid for all three backbones.

If `check_vram.py` shows DistilBERT is tight at batch 16, drop to 8 and double accumulation to 16. If MiniLM-L6 has headroom, try batch 32 with accumulation 4 — fewer accumulation steps means faster wall-clock training. Always adjust accumulation steps to compensate so effective batch size stays at 128.

Update `training_config.yaml` to store per-model overrides rather than a single shared configuration, so experiments are reproducible without manual parameter edits.

---

## Step 6 — Enable FP16 and Add Gradient Clipping

FP16 mixed-precision training is mandatory on the RTX 3060. Ampere Tensor Cores natively accelerate FP16 matrix operations, and enabling it roughly doubles throughput while cutting activation memory in half. Enable via `fp16=True` in `TrainingArguments`. The RTX 3060's Ampere architecture handles FP16 reliably — there are no Volta-era precision instabilities to worry about.

Gradient clipping at `max_grad_norm=1.0` must be explicitly set. This is not currently in `training_config.yaml` and needs to be added. It is the standard for all BERT fine-tuning and is especially important under FP16, where minority-class batches can produce large gradient magnitudes that overflow FP16 range and generate NaN loss. The symptom is training loss suddenly dropping to zero or going NaN. `max_grad_norm=1.0` prevents this.

---

## Step 7 — Handle Class Imbalance with Inverse-Frequency Weighted Cross-Entropy

Your training split has Code Injection at 3.51% (5,613 samples) versus SQL Injection at 46.74% (74,723 samples) — a 13:1 ratio. Standard unweighted cross-entropy will cause the model to largely ignore Code Injection because predicting it wrong costs the loss function very little. This produces high accuracy but collapsed Macro-F1 on the minority class — exactly the metric your capstone evaluates on.

Inverse-frequency weighted cross-entropy is the correct baseline fix. Compute class weights at runtime from the training parquet as `weight_c = total_samples / (num_classes × count_c)` and pass them to `nn.CrossEntropyLoss(weight=class_weights.to(device))`. Compute dynamically — do not hardcode — so weights update automatically if the dataset changes. The `training_config.yaml` already has `class_weighted_loss: yes`; this plan formalizes the implementation.

For a 13:1 imbalance, weighted cross-entropy is the recommended starting point. Focal loss is a valid alternative but adds a hyperparameter (gamma) that requires tuning and complicates thesis methodology justification. Start with weighted cross-entropy and only move to focal loss if Code Injection recall remains unacceptable after the first complete training run.

---

## Step 8 — Fine-Tune All Layers with Two AdamW Parameter Groups

Do not freeze encoder layers. HTTP payload classification is a domain-adaptation task — the malicious syntax vocabulary (`SELECT`, `UNION`, `OR 1=1`, percent-encoded characters, JavaScript event handlers) is far from the general web text these models were pretrained on. Full fine-tuning of all layers is required to adapt the contextual representations to this domain.

AdamW weight decay must be applied with the correct parameter group split: weight decay applies to weight matrices, but NOT to bias terms or LayerNorm weights. Applying weight decay to LayerNorm and biases is incorrect and produces slightly degraded performance. Implement two parameter groups in the optimizer:

```python
no_decay = ["bias", "LayerNorm.weight"]
optimizer_grouped_parameters = [
    {"params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)], "weight_decay": 0.01},
    {"params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], "weight_decay": 0.0},
]
optimizer = AdamW(optimizer_grouped_parameters, lr=2e-5)
```

This is the standard recipe from the original BERT fine-tuning paper and is the pattern used in Hugging Face's own classifier examples. The learning rate of 2e-5 is in the validated range (1e-5 to 5e-5) for full BERT-family fine-tuning.

---

## Step 9 — Implement Linear Warmup Correctly at Runtime

The 6% warmup in `training_config.yaml` must be computed at runtime, not hardcoded as a step count. The formula is:

```
total_steps = ceil(len(train_dataset) / effective_batch_size) × num_epochs
warmup_steps = int(0.06 × total_steps)
```

With 159,873 training samples, effective batch size 128, and 5 epochs max: `total_steps ≈ 6245`, `warmup_steps ≈ 375`. Use `get_linear_schedule_with_warmup(optimizer, num_warmup_steps, num_training_steps)` from `transformers`. Do not write a custom scheduler.

---

## Step 10 — Implement Early Stopping on Validation Macro-F1

Early stopping with patience=3 must monitor Macro-F1 on the validation set, not validation loss. This distinction matters with imbalanced data: loss can decrease (the model is getting better at majority classes) while Macro-F1 plateaus or drops (Code Injection recall is degrading). Saving based on loss would preserve the wrong checkpoint.

Configure in `TrainingArguments` with `load_best_model_at_end=True`, `metric_for_best_model="eval_macro_f1"`, and `greater_is_better=True`. Evaluation should run at the end of each epoch (`evaluation_strategy="epoch"`, `save_strategy="epoch"`). With 5 epochs max and patience=3, the minimum training run is 4 epochs and maximum is 5. Confirm the early stopping callback is active in the Trainer setup.

---

## Step 11 — Run Experiments in the Correct Order

With 6GB VRAM and a 159k training set, estimated training times per epoch at the configurations above are roughly:
- MiniLM-L6: ~8–12 minutes/epoch
- DistilBERT: ~15–20 minutes/epoch
- BERT-base: ~30–45 minutes/epoch (with gradient checkpointing)

The correct execution order is:

1. Run `check_vram.py` for all three models. Adjust batch configs if any model fails.
2. **Run MiniLM-L6 first.** It is the fastest and most VRAM-friendly. Use it to verify the full pipeline (data loading → tokenization → training loop → early stopping → checkpoint saving) works end-to-end before committing hours to BERT-base. If something is wrong with the data pipeline or loss function, you want to find out in 10 minutes, not 3 hours.
3. Run DistilBERT second. Validate that training is stable and metrics are reasonable.
4. Run BERT-base last. This is the most expensive run — gradient checkpointing enabled, batch size 8, accumulation 16. Monitor VRAM with `nvidia-smi` during the first 100 steps.
5. Apply temperature scaling calibration to all three checkpoints (see Step 12).
6. Evaluate all three calibrated models on the held-out test set.
7. MCDM selection based on Macro-F1, FPR, and CPU latency.
8. Optional: Re-run best model at `max_seq_len=256`. At 256, halve per-device batch size and double gradient accumulation steps to maintain effective batch 128. VRAM will be significantly tighter — run `check_vram.py` first.
9. Run DistilBERT with seeds 43 and 44 for the Phase 9 statistical requirement in `BUILD_GUIDE.md`.

---

## Step 12 — Apply Temperature Scaling After Training, Before Threshold Enforcement

This step is non-negotiable. Raw softmax outputs from fine-tuned transformers are systematically overconfident — a stated output of 80% does not mean the model is correct 80% of the time. Because your system assigns real enforcement actions (IP blocking, rate limiting, human review routing) based on whether the confidence score crosses 80% or 50%, deploying uncalibrated probabilities means your thresholds are arbitrary. An overconfident model will trigger far too many HIGH-confidence automated blocks, which is exactly the false-positive problem DICT is deploying this system to solve.

Temperature scaling (Guo et al., 2017) fits a single scalar T on the validation set by minimizing negative log-likelihood, then applies it at inference as `calibrated_logits = logits / T`. T > 1 softens overconfident distributions. For BERT-family classifiers, T typically falls between 1.5 and 3.

The implementation is a standalone `calibrate_model.py` script in `ml_model/training/` that: loads a checkpoint, runs inference over the validation set, fits T via `scipy.optimize.minimize_scalar` on validation NLL, saves T as a JSON file alongside the checkpoint, and produces a 10-bin reliability diagram. Expected Calibration Error (ECE) must be computed and reported before and after calibration for each model. These outputs are thesis-reportable evidence that your confidence thresholds are valid. This calibration step must be completed before any enforcement-tier metrics are evaluated or reported.

---

## Step 13 — Measure CPU Inference Latency on the Same Machine

The production deployment is CPU inference on the same Ryzen 7 6800H. You do not need a separate machine — just disable CUDA. Measure with:

```python
model = model.cpu()
model.eval()
# 10-sample warmup
for _ in range(10):
    _ = model(**inputs)
# Timed measurement
import time
times = []
for _ in range(100):
    start = time.perf_counter()
    with torch.no_grad():
        _ = model(**inputs)
    times.append(time.perf_counter() - start)
print(f"Mean: {np.mean(times)*1000:.1f}ms | p95: {np.percentile(times, 95)*1000:.1f}ms")
```

Load from the saved checkpoint (not the in-memory training copy) to simulate real cold-start inference behavior. If any model exceeds 100ms mean, the remediation path is ONNX Runtime export — the `ml_model/export/` directory in the project structure exists for this. MiniLM-L6 at 22.7M parameters should comfortably clear 100ms on the 6800H. DistilBERT is likely borderline. BERT-base is the most likely to exceed the target and may require ONNX quantization.

---

## Step 14 — Produce Versioned, Reproducible Artifacts for Every Run

Every training run outputs to `model_registry/staging/{model_name}_{dataset_version}_{timestamp}/` containing:

| Artifact | Content |
|----------|---------|
| `checkpoint/` | `model.save_pretrained()` + `tokenizer.save_pretrained()` |
| `training_log.json` | Per-epoch train loss, val loss, val Macro-F1, VRAM peak |
| `eval_report.json` | Per-class P/R/F1, confusion matrix, overall accuracy, FPR |
| `calibration/` | Temperature T value, ECE before/after, reliability diagram PNG |
| `config_used.yaml` | Exact copy of the training config at run time |
| `git_hash.txt` | Output of `git rev-parse HEAD` at run time |

No two runs overwrite each other. The seed is locked at 42 for the primary 3-way comparison. For the Phase 9 thesis statistical requirement, DistilBERT additionally runs with seeds 43 and 44 — report mean ± std across 3 seeds for all metrics.

---

## Summary: Key Changes to training_config.yaml

Add or update these fields before any training begins:

```yaml
max_grad_norm: 1.0            # ADD — not currently present

# Replace single batch config with per-model overrides:
models:
  minilm-l6:
    per_device_train_batch_size: 16
    gradient_accumulation_steps: 8
    gradient_checkpointing: false
  distilbert:
    per_device_train_batch_size: 16
    gradient_accumulation_steps: 8
    gradient_checkpointing: false
  bert-base:
    per_device_train_batch_size: 8
    gradient_accumulation_steps: 16
    gradient_checkpointing: true
```

All other fields (lr, warmup, epochs, early stop, FP16, seed, metric) remain as currently specified.

---

## Deliverable Summary

| File | Purpose |
|------|---------|
| `ml_model/training/check_vram.py` | Pre-flight VRAM audit per model — run before any training |
| `ml_model/training/data_loader.py` | Per-model tokenizer, offline tokenization with caching, DataCollatorWithPadding |
| `ml_model/training/train.py` | Full fine-tuning: weighted loss, two AdamW param groups, runtime warmup, early stop on Macro-F1, FP16, grad clip, gradient checkpointing (BERT-base) |
| `ml_model/training/calibrate_model.py` | Temperature scaling on validation, ECE + reliability diagram |
| `ml_model/training/evaluate.py` | Per-class metrics, confusion matrix, CPU latency on Ryzen 7 6800H |
| `model_registry/staging/{run_name}/` | All artifacts per run — checkpoint, log, eval, calibration, config, git hash |

---

## One-Line Strategic Summary

Fine-tune three plain transformers locally on 6GB VRAM using per-model batch configurations, gradient checkpointing for BERT-base, inverse-frequency loss weighting, and mandatory post-training temperature scaling — so the comparative evaluation is valid and the confidence scores your LOW/MEDIUM/HIGH enforcement thresholds rely on are actually calibrated probabilities.
