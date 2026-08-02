# Benchmark Evidence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen the benchmark evidence protocol around the benchmark notebooks and canonical Python modules so model training, evaluation, and reporting are thesis-defensible without relying on test-set winner selection, single-seed rankings, or incomplete deployment metrics.

**Architecture:** Keep the split benchmark notebook design, while placing reusable helpers in `ml_model/preprocessing`, `ml_model/training`, and `ml_model/evaluation`. The training notebook remains the artifact producer, the evaluation notebook remains the artifact consumer, and shared logic is imported from the canonical Python modules.

**Tech Stack:** Python, Jupyter notebooks, PyTorch, Hugging Face Transformers, NumPy, pandas, JSON/CSV/NPZ/PNG artifacts.

**Execution rule:** You must implement the edits in this run. Do not stop after producing a change map or plan.

---

## Scope Guardrails

- This plan applies to the benchmark notebooks and canonical ML source under `ml_model`.
- Keep the split:
  - `01_train_models.ipynb` stays training-focused.
  - `02_evaluate_models.ipynb` stays artifact-reader/reporter-focused.
- Do not silently keep weak evidence logic in place.
- After moving code, fix all imports immediately and keep notebook import cells runnable.
- Do not edit the original source notebook unless absolutely necessary for validation or traceability.
- Do not turn the evaluation notebook into a retraining notebook.
- Do not redesign the entire project or add new tracking frameworks.

## Files In Scope

**Modify**
- `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb`
- `ml_model\preprocessing\dataset_io.py`
- `ml_model\training\losses.py`
- `ml_model\evaluation\metrics.py`
- `ml_model\training\model_factory.py`

**Reference only unless forced by validation**
- `ml_model\notebooks\legacy\benchmark training.ipynb`

## Core Problems To Fix

1. Test-set winner selection is still being treated like model selection evidence.
2. Single-seed runs are too weak for serious ranking claims.
3. Split hygiene and leakage-resistance evidence are not surfaced clearly enough.
4. Model comparisons may be unfair if backbone comparisons mix different head architectures.
5. Deployment metrics like latency and model size exist in code but are not emitted as artifacts.
6. Checkpoint selection may not align with the real thesis objective.
7. Imbalance handling remains under-ablated.
8. Calibration reporting is too thin for confidence-gated security decisions.
9. Threshold-based operational security metrics are missing.
10. Robustness / evasion testing is missing.
11. Truncation evidence for `MAX_LEN=128` is missing or too weak.
12. Dead or misleading code and reporting language still exist.

---

### Task 1: Inspect The Current Training Workspace

**Files:**
- Read all six in-scope files

- [ ] Read `01_train_models.ipynb`, `02_evaluate_models.ipynb`, `io.py`, `losses.py`, `metrics.py`, and `models.py` completely.
- [ ] Trace the current control flow:
  training notebook -> saved artifacts under `results/` -> evaluation notebook reporting.
- [ ] Identify exactly where test metrics are being used to declare “best” models.
- [ ] Identify where seed handling exists and how many seeds are currently executed.
- [ ] Identify any current latency/model-size helpers and whether they are called.
- [ ] Identify where split metadata, truncation evidence, calibration outputs, and robustness checks are currently absent.
- [ ] Identify any local helper duplication that should be moved out of notebooks and into the Python modules.

**Deliverable:** a file-by-file change map before edits begin.

---

### Task 2: Remove Test-Set Winner Selection From Evaluation

**Files:**
- Modify: `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb`
- Modify: `ml_model\evaluation\metrics.py`

- [ ] Remove any reporting that chooses “best accuracy model,” “best macro-F1 model,” or “best calibrated ECE model” directly from test metrics.
- [ ] Redesign the evaluation notebook so it reads and reports test metrics as final evidence, not as the selector.
- [ ] If a selector remains, make it validation-based or driven by a pre-declared non-test rule saved in artifacts.
- [ ] Rename any misleading “best model” language so the notebook is clearly a reporter, not a hidden selector.

**Acceptance criteria**
- Test metrics are final-report outputs only.
- Evaluation notebook no longer performs test-based winner selection.

---

### Task 3: Add Multi-Seed Benchmark Support

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\preprocessing\dataset_io.py`
- Modify: `ml_model\evaluation\metrics.py`

- [ ] Replace the single-seed benchmark flow with an explicit seed list, minimum 3 seeds by default.
- [ ] Ensure the training notebook loops over seeds and persists each seed run cleanly.
- [ ] Save seed-level outputs with stable naming so aggregation is deterministic.
- [ ] Add aggregation outputs for mean and standard deviation across seeds at the model-summary level.
- [ ] Reduce display precision so single-run or aggregated metrics are not reported with false precision.

**Acceptance criteria**
- Benchmark artifacts capture at least 3 seeds per model by default.
- Comparison outputs can report mean ± std rather than single-run values alone.

---

### Task 4: Surface Split Hygiene And Leakage Evidence

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\preprocessing\dataset_io.py`

- [ ] Surface the split strategy used in the training notebook and save it in run metadata.
- [ ] Save or print exact split sizes and class distributions for train, validation, and test.
- [ ] Add artifact fields for deduplication status, zero cross-split overlap checks, near-duplicate handling status, and any label cleaning/quarantine notes if those are available from the prepared data pipeline.
- [ ] If exact evidence already exists in prepared split metadata, load and persist it instead of re-implementing it.
- [ ] If some proof cannot be generated from current artifacts, record that gap explicitly in the run manifest rather than pretending it is covered.

**Acceptance criteria**
- The run artifacts make split hygiene auditable.
- Leakage-resistance evidence is visible rather than implied.

---

### Task 5: Make Main Comparison Fair

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\training\model_factory.py`

- [ ] Inspect whether the main benchmark compares different backbones using different heads.
- [ ] For the main controlled benchmark, standardize the classifier head across models where practical.
- [ ] If different heads must remain, relabel the experiment clearly as architecture search rather than pure backbone comparison.
- [ ] Save the head type and architecture family explicitly in per-model metadata.

**Acceptance criteria**
- The main benchmark is either fair by construction or honestly labeled as architecture search.

---

### Task 6: Add Deployment Metrics To Artifacts

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\evaluation\metrics.py`

- [ ] Wire existing or new lightweight helpers so each model emits model size and inference latency artifacts.
- [ ] Save deployment metrics in per-model summary artifacts and in the comparison table.
- [ ] Use a minimal but honest latency protocol and record how it was measured.
- [ ] Remove unused deployment helpers if they will not be used.

**Acceptance criteria**
- Model size and latency are emitted for every compared model.
- There is no dead helper code pretending deployment metrics are covered.

---

### Task 7: Align Checkpoint Selection With Thesis Objective

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`

- [ ] Inspect the current best-checkpoint criterion.
- [ ] If it is driven only by validation focal loss, replace it with validation macro-F1 or a small justified validation-only composite that matches the actual thesis objective.
- [ ] Save the checkpoint selection rule into artifact metadata.
- [ ] Record the monitored metric in training history.

**Acceptance criteria**
- Best-checkpoint selection matches the benchmark goal rather than a proxy loss alone.

---

### Task 8: Add Imbalance Handling Ablations

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\training\losses.py`

- [ ] Define a small explicit ablation grid:
  - CE
  - weighted CE
  - focal
  - weighted focal
- [ ] Keep the implementation simple and artifact-friendly.
- [ ] Save the exact loss/weighting configuration for each run.
- [ ] Ensure the old unfair Code Injection weighting hack does not reappear silently.

**Acceptance criteria**
- Imbalance handling is compared explicitly, not assumed.

---

### Task 9: Expand Calibration Reporting

**Files:**
- Modify: `ml_model\evaluation\metrics.py`
- Modify: `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb`

- [ ] Keep temperature scaling fitted on validation only.
- [ ] Add NLL before/after calibration.
- [ ] Add reliability diagram output.
- [ ] Add per-class or top-label calibration reporting if practical.
- [ ] Add confidence-threshold behavior summaries for LOW / MEDIUM / HIGH bands.
- [ ] Do not present validation-calibrated ECE as the fair comparison metric.

**Acceptance criteria**
- Calibration artifacts are useful for confidence-gated security decisions, not just a single ECE number.

---

### Task 10: Add Threshold-Based Security Metrics

**Files:**
- Modify: `ml_model\evaluation\metrics.py`
- Modify: `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb`

- [ ] Add false positive rate for `Normal`.
- [ ] Add attack -> `Normal` escape rate summaries.
- [ ] Add per-class recall at multiple confidence thresholds.
- [ ] Add precision/recall/coverage summaries for LOW, MEDIUM, and HIGH confidence bands.
- [ ] Save these outputs in simple JSON/CSV formats.

**Acceptance criteria**
- The benchmark reflects security-operational behavior, not just plain classification metrics.

---

### Task 11: Add Robustness / Evasion Evaluation

**Files:**
- Modify: `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb`
- Modify: `ml_model\evaluation\metrics.py`
- Modify: `ml_model\preprocessing\dataset_io.py` if artifact helpers are needed

- [ ] Add a controlled perturbation evaluation suite for representative evasion variants:
  URL/percent encoding, case changes, whitespace injection, comment injection, fragmentation-style variants, and normalization edge cases.
- [ ] Keep this as evaluation-only; do not retrain.
- [ ] Save robustness retention metrics and failure examples as artifacts.
- [ ] Record exactly which perturbations were applied.

**Acceptance criteria**
- The evaluation notebook includes explicit robustness/evasion evidence.

---

### Task 12: Add Truncation Evidence

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: `ml_model\notebooks\benchmarks\02_evaluate_models.ipynb` if comparative reporting is added

- [ ] Compute token-length distribution on the current cleaned dataset splits.
- [ ] Save truncation rate artifacts for the configured `MAX_LEN`.
- [ ] Explain whether `MAX_LEN=128` is justified on the current dataset.
- [ ] If practical, add a small truncation ablation or at least an evidence summary that shows the cost of truncation.

**Acceptance criteria**
- `MAX_LEN` is evidenced, not assumed.

---

### Task 13: Clean Dead Or Misleading Code

**Files:**
- Modify any of the six in-scope files as needed

- [ ] Remove unused constants such as `HEADROOM_MB` if they are truly dead.
- [ ] Remove or wire up any leftover latency/model-size helpers.
- [ ] Remove any no-op experimental knobs that no longer affect training.
- [ ] Reduce metric display precision to a defensible level.

**Acceptance criteria**
- No obviously dead benchmark logic remains in the training workspace.

---

### Task 14: Improve Reproducibility And Logging

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`

- [ ] Add CuDNN determinism settings in `seed_everything()` if stronger reproducibility claims are intended.
- [ ] Log learning rate during training history so scheduler behavior is visible.
- [ ] Remove redundant second validation inference if the exact same saved best validation logits are already available.

**Acceptance criteria**
- Reproducibility and training-history artifacts are stronger and less redundant.

---

### Task 15: Push More Core Logic Into Modules

**Files:**
- Modify: `ml_model\notebooks\benchmarks\01_train_models.ipynb`
- Modify: one or more of `io.py`, `losses.py`, `metrics.py`, `models.py`

- [ ] Keep the notebooks orchestration-focused.
- [ ] Move reusable training/evaluation logic into the Python modules where that reduces notebook duplication.
- [ ] Keep module boundaries simple and explicit.

**Acceptance criteria**
- The notebooks are thinner and the core logic is easier to test and maintain.

---

### Task 16: Validate Honestly

**Files:**
- Modify only if validation finds breakage

- [ ] Run Python syntax validation for `io.py`, `losses.py`, `metrics.py`, and `models.py`.
- [ ] Validate notebook JSON structure.
- [ ] Confirm notebook import cells run after any refactor.
- [ ] Confirm the evaluation notebook does not contain a training loop.
- [ ] Confirm test-set metrics are no longer used for winner selection.
- [ ] Confirm multi-seed outputs are written and aggregatable.
- [ ] Confirm latency, size, calibration, threshold, and robustness outputs are actually emitted if claimed.
- [ ] If full training is too expensive, run the smallest honest smoke test:
  one model only,
  one minimal subset or shortened pass,
  enough to prove the training notebook emits artifacts and the evaluation notebook can load and report them.
- [ ] Report exactly what was and was not executed.

**Acceptance criteria**
- No success claim is made without a matching validation step.

---

## Expected Target State

1. **Controlled benchmark phase**
   Same preprocessing, same splits, same head, same training budget, same hardware assumptions, 3 to 5 seeds, and no test-based winner selection.

2. **Architecture exploration phase**
   If enhanced heads remain, they are clearly labeled as architecture-search experiments rather than pure backbone ranking.

3. **Deployment-aware comparison**
   Artifacts report macro-F1, per-class metrics, calibration, latency, size, false positives, attack escapes, and robustness retention.

4. **Confidence-aware operational reporting**
   Artifacts include threshold curves and confidence-band behavior aligned with LOW / MEDIUM / HIGH decision use.

## Priority Order

**Do first**
1. Remove test-set winner selection.
2. Add 3-seed support.
3. Emit latency and model size artifacts.
4. Surface split hygiene evidence.
5. Control or relabel classifier-head fairness.

**Do second**
6. Align checkpoint selection to validation macro-F1 or a justified validation-only rule.
7. Add imbalance ablations.
8. Add richer calibration outputs.
9. Add threshold-based operational metrics.
10. Add robustness/evasion tests.

**Do third**
11. Add truncation analysis.
12. Clean dead code.
13. Reduce false precision.
14. Improve determinism and LR logging.
15. Move more reusable logic into modules.

## Out Of Scope

- Whole-repo redesign
- Non-training/non-evaluation documentation work
- New experiment-tracking frameworks
- Thesis document rewriting
- Moving the benchmark system out of the current training workspace

## Assumptions

- The current `results/` artifact root remains the output base for this workspace.
- The existing local helper modules are the right boundary for extracted logic.
- Some split-hygiene evidence may depend on metadata produced upstream; if unavailable, the gap must be recorded rather than hidden.
- A full multi-seed benchmark may be too expensive for one run, so a minimal smoke path is acceptable only if it proves artifact emission and artifact loading honestly.
