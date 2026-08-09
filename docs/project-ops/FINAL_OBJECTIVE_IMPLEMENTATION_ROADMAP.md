# Final Objective Implementation Roadmap

> **Status:** Planning document only. This roadmap does not claim that production daily retraining is implemented or operational.
>
> **Scope:** Controlled, offline 20-day cumulative retraining simulation using prepared and verified daily batches. It does not authorize automatic production retraining, automatic model promotion, or production model-registry mutation.

## Goal

Build and evaluate a reproducible 20-day controlled retraining simulation for the native DistilBERT HTTP injection classifier. The experiment must investigate and address the false positive involving:

```text
GET /api/users?page=1&limit=10
```

The final result must show whether cumulative training with prepared benign and attack batches improves the classifier without increasing attack escapes, damaging confidence-based response actions, or breaking model packaging and backend loading.

## Architecture

The experiment will use the existing script-first training, evaluation, packaging, and backend model-loading boundaries. New orchestration should validate prepared batches, create cumulative dataset snapshots, run existing training and evaluation commands, package challenger artifacts, perform reload and backend checks, and record accepted or rejected candidates.

The 20 days are simulated data snapshots, not epochs and not real calendar days. Each day adds a reviewed batch to the historical training pool. The locked golden test set remains outside training and validation for the entire experiment.

## Technology and repository boundaries

- Python and the repository’s existing PyTorch/Hugging Face training stack.
- TOML configuration under `ml_model/configs/`.
- Existing native DistilBERT workflow under `ml_model/training/`.
- Existing evaluation workflow under `ml_model/evaluation/`.
- Existing packaging and promotion validation under `ml_model/export/`.
- Existing runtime model boundary at `web_app/services/model_service.py`.
- `pathlib.Path` for filesystem operations.
- JSONL/JSON/Parquet and SHA-256 manifests for experiment inputs and outputs where appropriate.
- No new scheduler, queue, database migration, cloud service, MLflow installation, or dashboard training button unless separately approved.

## Current repository facts that affect this roadmap

1. `ml_model/retraining/` documents a planned flow but does not contain a runnable daily retraining service or scheduler.
2. `ml_model/training/train.py` is the canonical training entrypoint and does not automatically promote models.
3. `ml_model/evaluation/evaluate.py` validates completed run bundles and creates evaluation summaries.
4. `data/processed/v3_907k_cleaned/` is the current established dataset and must not be overwritten casually.
5. The current training and staged-artifact path uses the established v1 preprocessing contract. The newer v2 preprocessing path must be treated as a separate experiment, not mixed into the primary data-correction experiment.
6. Existing backend tests commonly use a mock model through `tests/conftest.py`; successful mock tests do not prove that the real candidate artifact loads in the backend.
7. Existing untracked user files must remain untouched:
   - `docs/project-ops/DAILY_RETRAINING_JOURNAL.md`
   - `docs/project-ops/PR7_Sections_3B_3C_Implementation_Design.md`
8. Generated model artifacts, checkpoints, logs, and large datasets must remain ignored unless an intentionally small reproducibility fixture is approved for version control.

## Refinements required before implementation

The following decisions override any older or more general planning language:

1. **This is one implementation PR.** Do not create separate PRs for the golden evaluator, batch validator, simulator, tests, packaging checks, or documentation. Use focused commits within one branch and one PR. A second PR is justified only if a separately scoped demo-website change is genuinely required; no such change is currently identified.
2. **The experiment uses prepared batches, not live production reviews.** The batches may be curated or synthetic, but every sample must carry provenance and a verified ground-truth label. Reports must call the result a controlled simulation.
3. **The primary experiment uses the established v1 preprocessing and native DistilBERT path.** The v2 model-input/dataset path is a separate ablation and must not be mixed into the primary data-correction conclusion.
4. **The existing review database is not the immediate experiment input.** `traffic_label_reviews` records reviewed revisions, but the exporter is not implemented and legacy v1 rows are not eligible for approved training when canonical text is unavailable. The first experiment therefore uses prepared, validated files. A future exporter is separate work.
5. **The exact request remains a locked evaluation control.** Do not add `GET /api/users?page=1&limit=10` to training merely to make the test pass. Add diverse, structurally related benign examples instead.
6. **Daily candidates are evaluated, not automatically promoted.** Candidate packaging and reload are required; production registry mutation, automatic staging replacement, scheduler creation, and dashboard-triggered training are out of scope.
7. **Generated outputs stay outside Git.** Commit code, configuration, schemas, small safe fixtures, and summarized reports only. Do not commit checkpoints, private traffic, ordinary logs, or full generated datasets.
8. **Implementation and training happen on different machines.** The development PC completes the code, tests, configuration, fixtures, and smoke simulation. The laptop performs the expensive real baseline, corrected training, three-seed confirmation, and full 20-day simulation after synchronization. The implementation must include a verified laptop handoff document with exact commands and expected output paths.

## Proposed numerical gates

The final values must be written into the experiment TOML before candidate results are inspected. The following are starting proposals, not external standards:

- Mandatory benign controls: 100% expected label and expected action.
- Mandatory attack controls: 100% expected label and expected action.
- Normal false-positive rate: no more than baseline plus `0.001`.
- Attack escape rate: no more than baseline plus `0.001`.
- Macro F1: no decrease greater than `0.002` from baseline.
- Normal recall: at least `0.995`.
- Per-class supported-attack recall: no decrease greater than `0.01` from baseline.
- Label mapping, preprocessing version, thresholds, and response-action mapping: unchanged.
- Packaging, reload, backend health, and required smoke controls: pass.

The baseline must be regenerated before these gates are frozen. If sample counts make a rate tolerance statistically unstable, document the revised count-aware threshold before evaluating candidates; never change it after seeing candidate outcomes.

## One-PR implementation shape

The implementation should normally use one feature branch and one pull request with these focused commits:

1. `docs: define controlled retraining experiment contract`
2. `test: add locked golden-control evaluation`
3. `feat: validate prepared retraining batches`
4. `feat: add cumulative retraining simulation orchestration`
5. `test: cover simulation gates and failure handling`
6. `docs: add experiment runbook and reporting requirements`

The 20-day training outputs are generated after the code is validated and are not a reason to create another PR. Commit only safe summary reports if the experiment output is appropriate for version control.

## Evidence basis and design principles

The roadmap follows these evidence-backed principles:

- Use balanced accuracy, macro metrics, and per-class metrics for imbalanced classification. [Scikit-learn model evaluation documentation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- Prevent duplicate and group leakage with duplicate-aware and group-aware splits. [Scikit-learn cross-validation documentation](https://scikit-learn.org/stable/modules/cross_validation.html)
- Use cumulative replay instead of training only on the newest batch to reduce catastrophic forgetting. [Kirkpatrick et al., *Overcoming Catastrophic Forgetting*](https://doi.org/10.1073/PNAS.1611835114); [Replay or Regret: Evaluating Continual Learning Methods for Robust Intrusion Detection](https://doi.org/10.1109/MILCOM64451.2025.11310341)
- Use validation-based early stopping and best-checkpoint selection. [Hugging Face Trainer callbacks](https://huggingface.co/docs/transformers/main/trainer_callbacks)
- Record environment and seed information without claiming exact cross-platform reproducibility. [PyTorch reproducibility documentation](https://docs.pytorch.org/docs/stable/notes/randomness.html)
- Treat model promotion as staged validation with rollback. [AWS MLOps continuous-deployment guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/continuous-deployment.html)
- Protect training data and provenance against poisoning and integrity failures. [OWASP Machine Learning Security Top 10](https://owasp.org/www-project-machine-learning-security-top-10/); [NIST Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf)
- Evaluate confidence calibration separately from classification accuracy. [Guo et al., *On Calibration of Modern Neural Networks*](https://proceedings.mlr.press/v70/guo17a.html)
- Use paired comparisons for current-versus-candidate predictions. [Dietterich, *Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms*](https://pubmed.ncbi.nlm.nih.gov/9744903/)

Practitioner discussions are useful as implementation hints, not as proof: [MLOps champion/challenger and rollback discussion](https://www.reddit.com/r/mlops/comments/1uwgrkk/what_does_an_industry_standard_mlops_procedure/), [regular retraining discussion](https://www.reddit.com/r/mlops/comments/yesgqw/hot_to_introduce_regular_retrain_as_part_of_pipeline_strategies/), and [failures without obvious drift](https://www.reddit.com/r/mlops/comments/1q1sryi/when_models_fail_without_drift_what_actually/).

---

# Roadmap overview

| Phase | Name | Required result | Can run in parallel? | Gate |
|---|---|---|---|---|
| 0 | Scope and controls | Approved experiment contract | No | Adviser/project-owner approval |
| 1 | Repository and pipeline audit | Verified architecture and request trace | Partly with Phase 2 | Audit complete |
| 2 | Research validation and methodology | Defensible thesis methodology | Partly with Phase 1 | Methodology review |
| 3 | Data-quality investigation | Root-cause and dataset report | After Phase 1 | Data decision recorded |
| 4 | Golden test-set construction | Locked `golden-v1` | After Phase 3 design, before training | Golden set frozen |
| 5 | Corrected training-pool preparation | Versioned corrected pool | After golden schema, before training | Dataset integrity gate |
| 6 | Evaluation and simulation tooling | Tested orchestration and reporting | After contract decisions | Two-day dry run passes |
| 7 | Baseline evaluation | Current-model baseline | After Phases 4 and 6 | Baseline frozen |
| 8 | One-seed corrected experiment | Seed-2026 challenger result | Sequential | Mandatory controls pass |
| 9 | Three-seed confirmation | Repeatability evidence | Sequential | Confirmation review |
| 10 | Twenty-day cumulative simulation | Days 1–20 reports | Sequential | Every day has a valid result |
| 11 | Ablations and statistics | Comparative thesis evidence | After primary experiment | Analysis review |
| 12 | Packaging and controlled staging | Reloadable candidate and rollback proof | Partly with Phase 11 | Staging checks pass |
| 13 | Documentation and final assessment | Thesis-ready final package | After all results | Final assessment |

---

# Phase 0 — Scope, requirements, and experiment contract

## Purpose

Freeze what the experiment is allowed to prove and prevent scope drift into production automation.

## Essential tasks

1. Define the primary research question:

   > Does cumulative retraining with prepared, verified daily HTTP request batches reduce benign false positives while preserving attack detection and response-action correctness?

2. Define the secondary questions:

   - Is the false positive caused by missing benign examples, incorrect labels, preprocessing, or policy mapping?
   - Does cumulative replay reduce regressions compared with newest-only training?
   - Are improvements stable across seeds?
   - Do improvements survive packaging and backend reload?

3. Define non-goals:

   - No production scheduler.
   - No automatic production model promotion.
   - No online learning from unverified predictions.
   - No dashboard button that starts long-running training.
   - No claim that prepared batches represent real daily production traffic.

4. Freeze the model architecture:

   - Native DistilBERT sequence classifier.
   - Existing label mapping.
   - Existing preprocessing contract for the primary experiment.
   - Existing confidence thresholds and response-action mapping.

5. Freeze the seed policy:

   - Daily simulation: seed `2026`.
   - Confirmation: seeds `42`, `1337`, and `2026`.

## Outputs

- Experiment charter.
- Scope and non-goals section.
- Decision log.
- Initial acceptance criteria.
- Adviser review questions.

## Dependencies

- Existing training and serving contract.
- Current staged model identity.
- Existing class labels and action mapping.

## Success criteria

- A reviewer can state exactly what the experiment proves and does not prove.
- The exact request and its expected outcome are recorded.
- No production change is required to run the experiment.

## Risks and contingency

- If the research question changes after training begins, stop the experiment and create a new experiment version rather than changing the protocol silently.
- If the current model identity is uncertain, stop before baseline evaluation and resolve the artifact manifest first.

---

# Phase 1 — Repository and pipeline audit

## Purpose

Verify the actual implementation rather than relying on filenames, plans, or historical notes.

## Essential tasks

Inspect and document:

- `data/clean_907k.py`.
- `ml_model/preprocessing/`.
- `ml_model/training/train.py`.
- `ml_model/training/config.py`.
- `ml_model/training/model_factory.py`.
- `ml_model/evaluation/evaluate.py`.
- `ml_model/export/`.
- `web_app/services/model_service.py`.
- Relevant backend, WAF, and dashboard tests.
- Current staged model manifest and evaluation metadata.

Trace the exact request through:

```text
raw HTTP request
→ parser
→ normalized request
→ model input text
→ tokenizer
→ model output
→ probabilities
→ predicted label
→ confidence tier
→ response action
→ backend/WAF/dashboard output
```

Record whether the request is present in:

- Raw data.
- Processed data.
- Training split.
- Validation split.
- Test split.
- Golden controls.

## Outputs

- Repository audit report.
- Architecture flow diagram.
- Exact-request trace.
- Current-model identity record.
- List of confirmed, partial, missing, and unknown components.

## Tools and resources

- `rg` and `rg --files`.
- Python/Parquet inspection scripts.
- Existing training and evaluation commands.
- `git status`, `git log`, and artifact manifests.

## Success criteria

- Every claim about the workflow has a file, function, manifest, test, or command as evidence.
- The current model can be identified by artifact path and hash.
- The false-positive path is reproducible locally.

## Risks and contingency

- If the backend tests use a mock model, label that evidence separately and run a real-artifact reload test.
- If v1 and v2 preprocessing are both present, select one for the primary experiment and document the other as a separate ablation.

---

# Phase 2 — Research validation and thesis methodology

## Purpose

Turn the research findings into explicit design decisions instead of generic best-practice statements.

## Essential tasks

Document the justification for:

- Imbalanced-class metrics.
- Duplicate-aware and group-aware splitting.
- Locked golden evaluation.
- Cumulative replay.
- Early stopping.
- Repeated seeds.
- Calibration metrics.
- Paired model comparison.
- Manual challenger approval.
- Provenance and rollback.

For every technique, state:

- The problem it solves.
- Why it applies to this project.
- Implementation cost.
- Thesis value.
- What complexity is intentionally rejected.

## Outputs

- Research and engineering brief.
- Thesis methodology draft.
- Sources grouped into official guidance, academic research, industry guidance, and community observations.
- Threats-to-validity outline.

## Success criteria

- The adviser can distinguish published evidence, engineering convention, and project-specific inference.
- Every selected practice is connected to the pagination false-positive problem or to safe model evaluation.

---

# Phase 3 — Data-quality investigation

## Purpose

Determine whether the false positive is caused by data quality, coverage, leakage, preprocessing, or policy mapping.

## Essential measurements

Calculate and record:

- Sample count per class.
- Unique sample count per class.
- Exact duplicate rate.
- Near-duplicate rate.
- Conflicting-label groups.
- Request-method distribution.
- Request length distribution.
- Query-parameter frequency.
- Pagination, filtering, sorting, and search coverage.
- Data-source distribution.
- Train/validation/test overlap.
- Golden-set overlap.
- Label distribution by source and endpoint family.

## Investigation decisions

If the exact request is incorrectly labelled:

- Record original label.
- Record corrected label.
- Record reviewer and reason.
- Create a new dataset version.
- Identify affected duplicates and near-duplicates.
- State whether previous results are invalidated.

If the request is absent or correctly labelled but misclassified:

- Keep the exact request in the golden set.
- Add diverse, verified, structurally related benign examples.
- Do not copy the exact request into training.

## Outputs

- Dataset-quality report.
- Root-cause analysis.
- Data correction decision.
- Candidate corrected dataset specification.

## Success criteria

- The primary cause is classified as confirmed, likely, possible, or unknown.
- No training correction is made without provenance and review evidence.

## Risks and contingency

- If the cause remains uncertain, run a controlled ablation rather than claiming a definitive root cause.
- If conflicts are found, quarantine them and do not use them as labels until reviewed.

---

# Phase 4 — Locked golden test set

## Proposed files

```text
data/experiments/retraining_20_day_v1/golden/
├── golden_cases.jsonl
├── golden_manifest.json
└── README.md
```

## Essential categories

- Normal API requests.
- Pagination.
- Filtering.
- Sorting.
- Search.
- Normal GET and POST requests.
- Benign security-related documentation.
- SQL injection.
- Code injection.
- Command injection.
- Other supported attacks.
- Encoded and obfuscated attacks.
- Empty, malformed, oversized, and boundary inputs.

## Required controls

The exact failed request must be present with:

```text
expected_label = Normal
expected_action = ALLOWED
```

## Locking procedure

1. Create cases.
2. Review expected labels and actions.
3. Check exact and near-duplicate overlap with training data.
4. Remove overlap or document a new control.
5. Compute SHA-256.
6. Record version `golden-v1`.
7. Freeze before candidate results are examined.

## Outputs

- Locked golden set.
- Reviewer decisions.
- Golden-set hash.
- Category coverage report.

## Success criteria

- The golden set is independent of training and validation.
- All mandatory controls have an expected label and expected action.
- The exact request is not included in training.

---

# Phase 5 — Corrected training-pool preparation

## Proposed data contract

Each prepared sample should contain:

```text
sample_id
model_input_text
ground_truth_label
batch_day
source_type
is_synthetic
review_status
provenance_id
preprocessing_version
```

Predicted labels and prediction confidence must not be treated as ground truth.

## Essential tasks

- Create a new versioned training-pool output; never overwrite `data/processed/v3_907k_cleaned/`.
- Require verified labels.
- Validate label vocabulary.
- Require preprocessing-version compatibility.
- Remove exact overlap with golden cases.
- Check near-duplicate overlap where practical.
- Check conflicting labels.
- Preserve historical data for cumulative replay.
- Include structurally diverse benign HTTP traffic.

## Outputs

- Corrected training-pool version.
- Dataset manifest.
- Dataset hashes.
- Label and class-distribution report.
- Quarantine report.

## Success criteria

- The dataset can be reconstructed from its source files and configuration.
- No golden example is used for training.
- No unverified prediction is used as a label.

## Risks and contingency

- If prepared data is too small, report the limitation rather than generating repetitive variations.
- If the v2 preprocessing dataset is needed, make it a separate experiment version instead of changing the primary v1 result.

---

# Phase 6 — Evaluation and simulation tooling

## Proposed files

```text
ml_model/evaluation/golden_controls.py
ml_model/retraining/validate_batch.py
ml_model/retraining/simulate_20_day.py
ml_model/retraining/report_simulation.py
ml_model/configs/experiments/retraining_20_day_v1.toml
tests/unit/test_golden_controls.py
tests/unit/test_retraining_batch_validation.py
tests/unit/test_retraining_simulation.py
```

## Responsibilities

### `golden_controls.py`

- Load and hash-validate the locked golden set.
- Run predictions.
- Compare predicted labels with expected labels.
- Compare final actions with expected actions.
- Produce category and mandatory-control results.

### `validate_batch.py`

- Validate schema and label vocabulary.
- Require verified labels and provenance.
- Reject missing or unknown preprocessing versions.
- Detect duplicates and conflicts.
- Reject golden-set overlap.
- Produce a deterministic validation report.

### `simulate_20_day.py`

- Load historical data.
- Add Day 1 through Day N cumulatively.
- Create an immutable snapshot manifest.
- Call the existing training entrypoint.
- Call the existing evaluation entrypoint.
- Package the candidate.
- Reload-test the candidate.
- Run golden and backend checks.
- Apply frozen acceptance criteria.
- Record `ACCEPTED` or `REJECTED` without changing the active production model.

### `report_simulation.py`

- Aggregate daily metrics.
- Produce trend tables and charts.
- Report rejected candidates.
- Report mandatory-control failures.
- Report artifact and dataset hashes.

## Essential tests

- Invalid label rejection.
- Missing provenance rejection.
- Duplicate rejection.
- Golden overlap rejection.
- Cumulative snapshot correctness.
- Day isolation and deterministic rerun.
- Failure preservation.
- Candidate rejection when a mandatory control fails.
- No writes to the active production registry.

## First validation command

Run a two-day bounded simulation with synthetic fixtures before using the real prepared batches. The fixture must use tiny data and a mock or tiny model path so that the orchestration can be tested without a long GPU run.

## Success criteria

- A two-day dry run creates complete manifests and reports.
- Repeating the dry run with the same inputs produces identical input hashes and equivalent decisions.
- A deliberate failure is recorded as rejected instead of being silently ignored.

---

# Phase 7 — Current-model baseline

## Essential tasks

Evaluate the current staged model on:

- Existing validation and test data.
- Locked golden set.
- Exact pagination request.
- Backend real-artifact prediction path.
- Packaging and reload checks.
- WAF and dashboard smoke paths where available.

## Required baseline metrics

- Accuracy.
- Balanced accuracy.
- Per-class precision, recall, and F1.
- Macro and weighted F1.
- Normal false-positive rate.
- Attack escape rate.
- Normal recall.
- Calibration metrics.
- Confidence-tier distribution.
- Response-action outcomes.
- Inference latency.
- Model size and memory use.

## Outputs

- Baseline report.
- Baseline artifact manifest.
- Baseline golden predictions.
- Frozen numerical promotion thresholds.

## Gate

The baseline must be complete before candidate results are judged. Do not define tolerances after seeing candidate performance.

---

# Phase 8 — One-seed corrected-model experiment

## Configuration

```text
Architecture: native DistilBERT sequence classifier
Seed: 2026
Preprocessing: current primary contract
Maximum epochs: 4
Checkpoint: best validation checkpoint
Training data: historical pool plus corrected verified samples
Golden set: locked and excluded from training
```

## Tasks

1. Build the corrected dataset snapshot.
2. Validate its manifest and hashes.
3. Train the challenger.
4. Evaluate validation and test metrics.
5. Evaluate the golden set.
6. Check the exact pagination request.
7. Package the candidate.
8. Reload it from the packaged location.
9. Run real backend checks.
10. Compare against the baseline.

## Gate

Do not continue to three seeds if:

- The exact request is not `Normal` and `ALLOWED`.
- Any mandatory attack control fails.
- Packaging or reload fails.
- The candidate exceeds the false-positive, attack-escape, or macro-F1 tolerance.

Rejected candidates remain part of the research record.

---

# Phase 9 — Three-seed confirmation

## Tasks

Run the corrected configuration with:

```text
42
1337
2026
```

Report for each seed:

- Best epoch.
- Validation metrics.
- Test metrics.
- Golden-set results.
- Exact-request result.
- Normal false-positive rate.
- Attack escape rate.
- Calibration.
- Latency.

Then report:

- Mean.
- Standard deviation.
- Best result.
- Worst result.
- Whether every seed passes mandatory controls.
- Whether the conclusion changes by seed.

## Gate

Proceed to the 20-day simulation only if the conclusion is stable enough to justify the simulation. A single lucky seed must not be presented as confirmation.

---

# Phase 10 — Twenty-day cumulative simulation

## Daily procedure

For each simulated day from 1 through 20:

1. Load the prepared daily batch.
2. Validate schema, labels, provenance, and preprocessing version.
3. Check exact duplicates, conflicts, and golden overlap.
4. Combine the batch cumulatively with historical data and prior batches.
5. Create a versioned dataset snapshot.
6. Train using the fixed configuration and seed `2026`.
7. Select the best validation checkpoint.
8. Package the candidate.
9. Reload-test the package.
10. Evaluate on the same validation, test, and golden sets.
11. Run the exact request and mandatory controls.
12. Run backend and WAF checks where practical.
13. Apply the frozen gate.
14. Record accepted or rejected.
15. Preserve all artifacts, logs, hashes, and failure reasons.

## Daily drift-style measurements

Report changes in:

- Class distribution.
- Request methods.
- Request length.
- Query-parameter frequency.
- Attack category.
- Source distribution.
- Duplicate rate.
- Confidence distribution.
- Error categories.

These are experiment diagnostics, not proof of live production drift.

## Outputs

- Twenty daily run manifests.
- Twenty daily evaluation reports.
- Daily candidate decision table.
- Trend charts.
- Accepted/rejected summary.
- Final cumulative Day 20 artifact.

## Gate

The simulation is complete only when all 20 days have a valid result or an explicitly documented failure. Missing days must not be silently skipped.

---

# Phase 11 — Ablations and statistical analysis

## Essential ablations

1. Original data versus corrected labels.
2. Original normal-traffic pool versus expanded normal-traffic pool.
3. Cumulative training versus newest-only training.

## Optional ablation

4. Current preprocessing versus v2 preprocessing, only as a separately versioned experiment.

## Statistical analysis

- Use paired current-versus-candidate predictions.
- Use McNemar’s test where assumptions and sample size are appropriate.
- Use bootstrap confidence intervals where practical.
- Report absolute changes and effect sizes.
- Avoid claiming independence between cumulative daily snapshots.
- Explain limitations caused by synthetic data, repeated templates, and class imbalance.

## Outputs

- Ablation report.
- Statistical comparison report.
- Per-category error analysis.
- Thesis-ready figures and tables.

## Success criteria

- Every ablation answers one stated research question.
- Negative results are preserved.
- Statistical claims match the available sample size and experimental design.

---

# Phase 12 — Packaging, controlled staging, and rollback

## Essential tasks

Before any staging replacement:

1. Archive the current staged model.
2. Record the archive hash.
3. Record the current active model identity.
4. Validate the candidate manifest.
5. Validate preprocessing and label compatibility.
6. Package the candidate.
7. Reload it locally from the packaged path.
8. Run backend health checks.
9. Run benign and attack controls.
10. Confirm the old artifact remains available.

Use an atomic path replacement or the repository’s existing safe promotion mechanism. Do not write to the active production registry from the web application.

## Rollback procedure

If a critical check fails:

1. Restore the archived previous artifact.
2. Reload the service.
3. Confirm the previous identity and hash.
4. Rerun critical health and control checks.
5. Record the rollback reason.

The final status must be `ROLLED_BACK` if rollback was required. It must not be reported as a successful promotion.

## Optional enhancement

A staging-only challenger alias or blue/green path may be added later if the existing promotion tooling supports it without adding a new dependency. It is not required for the thesis simulation.

---

# Phase 13 — Final documentation and assessment

## Required deliverables

1. Research and best-practice brief.
2. Repository and pipeline audit.
3. Root-cause analysis of the benign false positive.
4. Dataset-quality report.
5. Locked golden-test-set specification.
6. Corrected data-preparation workflow.
7. Baseline evaluation report.
8. One-seed experiment report.
9. Three-seed confirmation report.
10. Twenty-day cumulative simulation report.
11. Ablation-study report.
12. Statistical comparison.
13. Promotion and rollback procedure.
14. Reproducibility manifest.
15. Thesis-ready methodology section.
16. Thesis-ready results section.
17. Limitations and threats-to-validity section.
18. Recommended future-work section.

## Required limitations

Explicitly discuss:

- Prepared batches are not real production daily data.
- Synthetic traffic may not represent real attackers.
- Labels may contain reviewer or source bias.
- The golden set may be too small for broad generalization.
- Duplicate and near-duplicate detection is imperfect.
- Hyperparameter decisions can introduce selection bias.
- Seed variability is limited to the selected seeds.
- Thresholds affect action results.
- Simulated days are not calendar-time drift.
- No external validation may be available.
- Dashboard and WAF tests may not exercise all deployment conditions.

## Final assessment statuses

Use one of:

- `SUCCESS` — all required experiment stages completed and acceptance criteria met.
- `ROLLED_BACK` — candidate was staged or promoted but critical checks required restoration.
- `BLOCKED` — a required dependency or validation could not be completed.
- `RESEARCH_COMPLETE_ONLY` — research and design completed, but implementation or experiment execution was not completed.

---

# Milestones and review checkpoints

| Milestone | Evidence required | Reviewer decision |
|---|---|---|
| M0 Scope frozen | Charter and non-goals | Approve experiment scope |
| M1 Audit complete | Repository audit and request trace | Confirm implementation facts |
| M2 Data decision | Root-cause and data-quality report | Approve correction or expansion |
| M3 Golden set locked | Manifest, reviewer decisions, hash | Freeze evaluation controls |
| M4 Tooling smoke complete | Two-day deterministic dry run | Approve real baseline |
| M5 Baseline frozen | Current-model metrics and artifact identity | Freeze thresholds |
| M6 One-seed complete | Candidate report and mandatory controls | Continue or reject |
| M7 Three-seed complete | Mean, standard deviation, worst seed | Confirm repeatability |
| M8 Day 20 complete | All daily manifests and decisions | Approve analysis |
| M9 Staging validation | Package, reload, backend, rollback evidence | Approve staging only |
| M10 Thesis package complete | Methods, results, limitations, sources | Adviser/final review |

---

# Responsibilities

| Role | Responsibility |
|---|---|
| Thesis owner/developer | Approves scope, reviews labels, runs local training, preserves evidence, decides whether a candidate may be staged |
| ML implementation role | Implements validation, orchestration, evaluation, manifests, and tests according to this roadmap |
| Backend/integration role | Verifies packaged artifact loading, backend health, WAF path, and response-action mapping |
| Security reviewer | Reviews data provenance, poisoning controls, secret handling, artifact integrity, and rollback |
| Adviser/research reviewer | Reviews methodology, acceptance thresholds, statistical interpretation, and thesis claims |
| CI environment | Runs deterministic unit and integration tests where configured; it does not replace laptop GPU validation |

For a solo project, these are review responsibilities rather than separate employees. The thesis owner should still perform the equivalent checkpoints explicitly.

---

# Parallel work opportunities

The following may proceed in parallel after the scope is frozen:

- Research brief writing and repository audit documentation.
- Golden-set schema design and batch schema design.
- Test-fixture preparation and report-template preparation.
- Packaging/reload test design and dataset audit scripts.
- Thesis methodology writing and implementation documentation.

The following must remain sequential:

```text
Audit → root-cause decision → golden-set lock → baseline → corrected model → three-seed confirmation → 20-day simulation → final analysis
```

Do not train candidates before the golden set and acceptance thresholds are frozen.

---

# Recommended implementation commits

The full implementation should normally be delivered in one pull request with focused commits:

1. `docs: define controlled retraining experiment contract`
2. `test: add locked golden control evaluation`
3. `feat: validate prepared retraining batches`
4. `feat: add cumulative retraining simulation orchestration`
5. `test: cover simulation failure and promotion gates`
6. `feat: add packaging reload and backend validation report`
7. `docs: add baseline and 20-day experiment runbook`
8. `docs: record experiment results and thesis limitations`

Each commit should leave the repository usable and should include the narrowest relevant tests.

---

# Validation strategy

## Unit validation

Test:

- Golden-set parsing and hash verification.
- Label and action expectations.
- Batch schema validation.
- Duplicate and conflict detection.
- Cumulative snapshot construction.
- Manifest generation.
- Acceptance-gate decisions.
- Rejection and failure recording.
- Production-registry write protection.

## Integration validation

Run:

- Existing ML training portability tests.
- Existing evaluation tests.
- Existing packaging tests.
- Real candidate reload test.
- Backend model-service test with the candidate artifact.
- WAF and dashboard smoke tests where available.

## Smoke validation

Before any large run:

- Use a tiny synthetic fixture.
- Run one or two simulated days.
- Use CPU or the laptop GPU with bounded samples.
- Confirm complete manifests and reports.
- Confirm failure handling with an intentionally invalid batch.

## Full validation

Only after smoke validation passes:

- Run the current baseline.
- Run seed `2026`.
- Run three seeds.
- Run all 20 cumulative snapshots.
- Run ablations.
- Run final packaging and controlled staging checks.

Do not treat a successful unit suite as proof of model quality or production readiness.

---

# Contingency plan

| Problem | Response |
|---|---|
| Exact request absent from data | Keep it golden-only; add diverse related benign samples, not the exact text |
| Incorrect label found | Quarantine and create a new dataset version with reviewer evidence |
| Golden overlap found | Remove overlap before locking or create a formally documented new golden version |
| GPU or CUDA failure | Run the bounded smoke on CPU; do not silently claim full training succeeded |
| Training run incomplete | Mark the run invalid and preserve failure metadata; do not evaluate partial artifacts |
| Packaging fails | Reject the candidate and investigate artifact contract compatibility |
| Backend reload fails | Do not stage or promote; retain current model |
| False-positive improvement causes attack escapes | Reject candidate and report the trade-off |
| Daily run fails | Record the day as failed; do not silently skip it or invent results |
| 20 days take too long | Keep one seed per daily snapshot and three-seed endpoint confirmation; reduce only through a documented protocol change |
| Preprocessing versions conflict | Keep v1 as the primary experiment and run v2 separately |
| Database or CI environment unavailable | Separate local model evidence from unavailable integration evidence; do not claim the check passed |

---

# Essential, recommended, and optional scope

## Essential

- Repository audit.
- Exact-request trace.
- Data-quality investigation.
- Locked golden set.
- Verified prepared batches.
- Cumulative replay.
- One-seed corrected experiment.
- Three-seed confirmation.
- Twenty daily reports.
- Baseline comparison.
- Packaging and reload validation.
- Backend checks.
- Hashes and manifests.
- Rejection and rollback procedure.
- Thesis methodology, results, and limitations.

## Recommended

- McNemar comparison.
- Bootstrap confidence intervals.
- Daily distribution and confidence trend reports.
- Cumulative-versus-newest-only ablation.
- Real-artifact backend smoke tests separate from mock tests.
- Staging-only challenger artifact.
- Adviser checkpoint at baseline and Day 20.

## Optional

- v2 preprocessing ablation.
- Additional hidden regression set.
- Blue/green staging path.
- Lightweight experiment dashboard generated from static reports.
- A future scheduler after real verified-label collection exists.

---

# Final completion checklist

- [ ] Scope and non-goals approved.
- [ ] Repository and current-model audit complete.
- [ ] Exact benign request traced end to end.
- [ ] Root cause classified or explicitly left uncertain.
- [ ] Dataset-quality report complete.
- [ ] Golden set reviewed, hashed, and locked.
- [ ] Prepared daily batches validated and frozen.
- [ ] Simulation tooling passes two-day dry run.
- [ ] Baseline metrics recorded.
- [ ] Acceptance thresholds frozen before candidate evaluation.
- [ ] Seed-2026 experiment complete.
- [ ] Three-seed confirmation complete.
- [ ] All 20 cumulative snapshots complete or explicitly documented as failed.
- [ ] Accepted and rejected candidates preserved.
- [ ] Ablations complete where applicable.
- [ ] Statistical comparison complete.
- [ ] Candidate packaging and reload verified.
- [ ] Backend, WAF, and dashboard checks recorded separately.
- [ ] Previous artifact archived before any staging replacement.
- [ ] Rollback procedure tested or explicitly marked unverified.
- [ ] Reproducibility manifests complete.
- [ ] Thesis methodology, results, limitations, and future work complete.
- [ ] No production daily automation is claimed without separate implementation and authorization.

## Immediate next action

Do not start the 20-day training yet. The first implementation task is to complete Phase 0 and Phase 1, then create and lock the golden set before changing the training pool.
