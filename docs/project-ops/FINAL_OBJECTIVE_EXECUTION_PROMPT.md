# Final Objective Execution Prompt

This file contains a self-contained prompt for a new AI coding agent. Copy only the text inside the `BEGIN PROMPT` and `END PROMPT` markers into a new coding-agent chat.

```text
BEGIN PROMPT

You are the senior machine-learning engineer, backend engineer, security reviewer, and thesis research assistant responsible for implementing the controlled retraining experiment in this repository.

Do not assume that plans, README files, historical reports, filenames, or previous AI summaries are implementation proof. Inspect the live repository, tests, manifests, configuration, and artifacts before changing anything.

Repository:

G:\AI\PDDDD\injection-alert-system

The repository is an academic HTTP injection-alert and analyst-triage system containing:

- FastAPI backend under `web_app/`.
- Next.js dashboard and BFF under `frontend/`.
- Native DistilBERT training under `ml_model/training/`.
- Evaluation under `ml_model/evaluation/`.
- Packaging and promotion validation under `ml_model/export/`.
- Model artifacts under `ml_model/model_registry/`.
- Processed datasets under `data/processed/`.
- Local WAF/OWASP CRS proof paths.

The relevant runtime architecture is:

```text
Browser → Next.js route handler/BFF → FastAPI → model service → confidence tier → response action
```

Do not bypass the BFF. Do not add direct browser-to-FastAPI calls.

# Objective

Implement and validate a reproducible, controlled 20-day cumulative retraining simulation for the native DistilBERT HTTP injection classifier.

The primary known regression is:

```text
GET /api/users?page=1&limit=10
```

This is benign pagination traffic and must be classified as:

- Label: `Normal`
- Final action: `ALLOWED`

The experiment must determine whether cumulative retraining with prepared and verified daily batches reduces benign false positives without increasing attack escapes, damaging confidence-based response actions, or breaking packaging and backend model loading.

The result must be described honestly as:

```text
A controlled offline 20-day retraining simulation using prepared daily batches.
```

It must not be described as real production daily retraining because the batches are prepared or synthetic rather than collected from twenty actual calendar days of reviewed production traffic.

# Existing architecture and constraints

Inspect and preserve these existing boundaries:

- `ml_model/training/train.py` is the canonical script-first training entrypoint.
- `ml_model/training/config.py` owns portable TOML training configuration.
- `ml_model/training/model_factory.py` supports native DistilBERT and historical architectures; the primary experiment must use native DistilBERT.
- `ml_model/evaluation/evaluate.py` validates completed run bundles and produces evaluation summaries.
- `ml_model/export/` owns packaging and promotion validation.
- `web_app/services/model_service.py` is the runtime model boundary.
- `ml_model/retraining/` currently documents a planned flow but does not contain a complete daily scheduler or runnable retraining service.
- `data/processed/v3_907k_cleaned/` is an existing established dataset and must not be overwritten casually.
- The current primary training and staged-artifact path uses the established v1 preprocessing contract.
- The newer v2 preprocessing/model-input path is a separate experiment and must not be mixed into the primary data-correction conclusion.
- Existing backend tests often use a mock model through `tests/conftest.py`; mock tests do not prove that a real candidate artifact loads.
- Existing untracked user files must be preserved and must not be staged accidentally:
  - `docs/project-ops/DAILY_RETRAINING_JOURNAL.md`
  - `docs/project-ops/PR7_Sections_3B_3C_Implementation_Design.md`
- Do not commit checkpoints, private datasets, generated logs, ordinary run outputs, secrets, or large model artifacts.
- Do not write to `ml_model/model_registry/production/` from the web application or from an automatic retraining flow.
- Do not change confidence thresholds, confidence/action mapping, label mapping, or the `BLOCKED`/`THROTTLED`/`ALLOWED` transport contract without explicit approval.
- Do not create a dashboard training button.
- Do not create a production scheduler, queue, database migration, or cloud training service for this task.
- Do not add MLflow, DVC, Kubernetes, Celery, or other infrastructure merely because it is common in larger organizations.
- Use existing dependencies and conventions wherever possible.

# Required workflow before editing

1. Read `AGENTS.md` and `docs/project-ops/FINAL_OBJECTIVE_IMPLEMENTATION_ROADMAP.md`.
2. Inspect the full repository state:
   - `git status --short`
   - `git branch --show-current`
   - `git log -5 --oneline`
   - `git diff --check`
3. Inspect the relevant source, tests, configurations, migrations, dataset metadata, model manifests, and `.gitignore` rules.
4. Search for hardcoded paths, model-input versions, label mappings, confidence thresholds, response actions, production-registry writes, scheduler code, and existing retraining placeholders.
5. Confirm the actual current staged model identity and artifact hash.
6. Confirm whether prepared daily batches and a golden set already exist. Do not invent that they exist.
7. Report assumptions and unknowns before implementation.

Preserve unrelated user changes. Never use `git reset --hard`, `git checkout --`, `Remove-Item`, or broad cleanup commands to hide unrelated work.

# Research and engineering basis

Use these sources to justify implementation decisions. Treat community discussions as anecdotal engineering input, not scientific proof.

- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- NIST SSDF: https://csrc.nist.gov/projects/ssdf
- OWASP ML Top 10: https://owasp.org/www-project-machine-learning-security-top-10/
- PyTorch reproducibility: https://docs.pytorch.org/docs/stable/notes/randomness.html
- Hugging Face early stopping: https://huggingface.co/docs/transformers/main/trainer_callbacks
- Scikit-learn evaluation: https://scikit-learn.org/stable/modules/model_evaluation.html
- Scikit-learn group-aware validation: https://scikit-learn.org/stable/modules/cross_validation.html
- AWS staged promotion and rollback: https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/continuous-deployment.html
- Guo et al. calibration research: https://proceedings.mlr.press/v70/guo17a.html
- Dietterich paired classifier tests: https://pubmed.ncbi.nlm.nih.gov/9744903/
- Kirkpatrick et al. catastrophic forgetting: https://doi.org/10.1073/PNAS.1611835114
- Replay and intrusion detection: https://doi.org/10.1109/MILCOM64451.2025.11310341
- Practitioner champion/challenger discussion: https://www.reddit.com/r/mlops/comments/1uwgrkk/what_does_an_industry_standard_mlops_procedure/
- Practitioner retraining discussion: https://www.reddit.com/r/mlops/comments/yesgqw/hot_to_introduce_regular_retrain_as_part_of_pipeline_strategies/

Use the simplest design that satisfies the evidence-backed controls. Do not introduce advanced continual-learning algorithms unless a separate approved ablation requires them. Cumulative historical replay is the primary design.

# One-PR and commit policy

Use one feature branch and one pull request for this implementation. Do not create separate PRs for the golden evaluator, batch validator, simulator, tests, packaging checks, or documentation.

If the branch does not already exist, create:

```text
feature/20-day-retraining-simulation
```

Do not use a `codex/` branch prefix unless the repository or user explicitly requires it.

Use focused commits, approximately:

1. `docs: define controlled retraining experiment contract`
2. `test: add locked golden-control evaluation`
3. `feat: validate prepared retraining batches`
4. `feat: add cumulative retraining simulation orchestration`
5. `test: cover simulation gates and failure handling`
6. `docs: add experiment runbook and reporting requirements`

Do not use `git add .`; stage files explicitly. Do not push or create a remote PR unless the user has authorized those external GitHub actions. If authorized, open or update only the one primary PR.

# Laptop execution boundary

The current coding-agent session is running on the development PC. The PC is responsible for completing and testing the repository implementation. The laptop is the approved machine for the expensive native DistilBERT training and the full 20-day simulation.

The coding agent must complete all repository work needed for laptop execution, including code, configuration, small synthetic fixtures, tests, documentation, portable paths, output-directory handling, and exact commands. It must not claim that the real baseline, one-seed run, three-seed run, or 20-day simulation was completed on the PC unless those commands were actually run and their artifacts were inspected.

The coding agent may run:

- Unit and integration tests.
- CPU smoke tests.
- Bounded GPU smoke tests if safe and available.
- A tiny one- or two-day orchestration dry run using synthetic fixtures.

The coding agent must leave these expensive operations as an explicit laptop handoff unless the user separately authorizes them on the current machine:

- Full baseline evaluation using the real model and complete dataset.
- Corrected one-seed training.
- Three-seed confirmation training.
- The complete 20-day cumulative simulation.
- Large ablations.

The final report must distinguish `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, and `REQUIRES_LAPTOP` for every training and evaluation step.

END OF CONTEXT SECTION

# Implementation sequence

## Task 1: Freeze the experiment contract

Create or update a small experiment configuration and documentation contract defining:

- Experiment name and version.
- Historical dataset version.
- Primary preprocessing version: the established v1 contract.
- Native DistilBERT model and immutable model revision.
- Daily seed: `2026`.
- Confirmation seeds: `42`, `1337`, `2026`.
- Maximum epoch count: four unless live repository evidence requires another value.
- Locked golden-set version.
- Label mapping.
- Confidence thresholds.
- Response-action mapping.
- Output directory.
- Acceptance tolerances.

Do not silently change these values between simulated days.

## Task 2: Add the locked golden-control contract

Follow existing repository conventions before choosing a path. If no equivalent exists, use:

```text
data/experiments/retraining_20_day_v1/golden/golden_cases.jsonl
data/experiments/retraining_20_day_v1/golden/golden_manifest.json
data/experiments/retraining_20_day_v1/golden/README.md
```

Each golden case must include at least:

- `case_id`
- `model_input_text`
- `expected_label`
- `expected_action`
- `category`
- `source_type`
- `rationale`
- `reviewer`
- `golden_version`
- `locked_at`

Include the exact pagination request as a mandatory benign control. Do not put the exact request in training.

Include normal pagination, filtering, sorting, search, API, encoded, malformed, boundary, SQL injection, code injection, command injection, other-attack, obfuscated, and false-negative controls.

Before locking:

1. Review labels and expected actions.
2. Detect exact and near-duplicate overlap with training and validation data.
3. Remove overlap or document why a case must remain.
4. Compute SHA-256.
5. Freeze `golden-v1`.

Implement a pure evaluator, preferably:

```text
ml_model/evaluation/golden_controls.py
```

It must validate the golden manifest hash, run the existing model-prediction boundary, report predicted label/probability/confidence/action, report per-category results, and fail the mandatory-control gate when expected outcomes are not met.

Add focused unit tests using temporary fixtures and a small fake model where appropriate.

## Task 3: Validate prepared daily batches

Follow existing data conventions. If no equivalent exists, use:

```text
data/experiments/retraining_20_day_v1/daily_batches/day_01.jsonl
...
data/experiments/retraining_20_day_v1/daily_batches/day_20.jsonl
```

Each sample must contain:

- `sample_id`
- `model_input_text`
- `ground_truth_label`
- `batch_day`
- `source_type`
- `is_synthetic`
- `review_status`
- `provenance_id`
- `preprocessing_version`

The validator must reject unknown labels, missing ground truth, predicted labels used as ground truth, unapproved samples, missing provenance, unknown preprocessing versions, exact duplicates, conflicting labels, and overlap with the locked golden set. It must produce deterministic validation reports and preserve rejected samples in a quarantine report rather than silently deleting them.

Prefer:

```text
ml_model/retraining/validate_batch.py
```

Add tests for every rejection condition.

Do not use live unverified model predictions as training labels. The current review exporter is not implemented; prepared files are the experiment input unless a verified exporter is found during audit.

## Task 4: Build cumulative snapshot creation

Implement a deterministic function that creates:

```text
Day 1 = historical data + Day 1
Day 2 = historical data + Day 1 + Day 2
...
Day 20 = historical data + Days 1–20
```

The snapshot builder must preserve the historical dataset, validation methodology, and locked golden set; reject duplicates and conflicts; record input/output hashes and class/source distributions; write to a versioned experiment output directory; and never overwrite `data/processed/v3_907k_cleaned/`.

Use `pathlib.Path` and repository/module anchors. Do not commit absolute drive paths.

## Task 5: Integrate existing training and evaluation

Do not duplicate the training loop. Call the maintained entrypoint under `ml_model/training/` and the evaluator under `ml_model/evaluation/`.

The simulator should:

1. Validate the batch.
2. Build the cumulative snapshot.
3. Resolve the portable TOML configuration.
4. Run native DistilBERT training.
5. Select the best validation checkpoint.
6. Validate run-bundle completeness.
7. Run the existing evaluator.
8. Package the candidate through the existing export boundary.
9. Reload-test the packaged artifact.
10. Run golden controls and the real backend model boundary.
11. Apply the acceptance gates.
12. Record `ACCEPTED` or `REJECTED`.

The simulator must never automatically modify the active production model.

Prefer:

```text
ml_model/retraining/simulate_20_day.py
ml_model/retraining/report_simulation.py
```

Do not start the full 20-day run on the development PC. The implementation must be ready for the laptop, but the full run is a later manual laptop operation after the code is synchronized and the two-day dry run and baseline prerequisites have passed.

## Task 6: Implement smoke mode and failure handling

The smoke mode must use tiny synthetic fixtures, one or two simulated days, CPU or bounded laptop-GPU execution, minimal samples, temporary directories, and no internet download during tests.

Test valid completion, invalid-batch rejection, training-failure preservation, incomplete-checkpoint rejection, packaging failure, mandatory-control failure, production-registry write protection, and deterministic reruns with identical input hashes.

The smoke mode proves orchestration startup and failure safety. It is not a model-quality result.

## Task 7: Prepare and, only when authorized, run the baseline

Before candidate training, prepare the exact baseline command and validation procedure. The full baseline using the complete dataset is a laptop operation unless the user explicitly authorizes it on the current PC. When it is run, evaluate the current staged model using the same golden set, split definitions, preprocessing, tokenizer, hardware where practical, thresholds, response mapping, and metric definitions.

Record model path/hash, architecture/revision, dataset/split hashes, per-class metrics, macro F1, balanced accuracy, normal false-positive rate, attack escape rate, normal recall, calibration, latency, memory, exact-request output/action, packaging, and reload status.

Only after this baseline is frozen may the numerical acceptance tolerances be finalized. If the baseline is not run in the coding-agent session, leave its status as `REQUIRES_LAPTOP` and provide the exact command and expected output files.

## Task 8: Prepare and, on the laptop, run the corrected one-seed experiment

Prepare a portable command and configuration for native DistilBERT, seed `2026`, established v1 preprocessing, historical data plus verified corrected/expanded samples, maximum four epochs unless evidence requires otherwise, and the best validation checkpoint. Run the real experiment on the laptop after synchronization unless explicitly authorized otherwise.

Evaluate against the baseline, locked golden set, exact request, existing test data, packaging/reload, real backend loading, and available WAF/dashboard smoke paths.

Do not promote the candidate merely because it improves one benign control. If training is deferred to the laptop, record `REQUIRES_LAPTOP` rather than presenting the implementation as experimentally complete.

## Task 9: Prepare and, on the laptop, run three-seed confirmation

Prepare the command and report procedure first. Run seeds `42`, `1337`, and `2026` only if the one-seed candidate passes mandatory blockers. This is a laptop operation unless explicitly authorized otherwise. Report each seed, mean, standard deviation, best, worst, class instability, golden results, false-positive/escape trends, calibration, and latency. Do not select only the best seed.

## Task 10: Prepare and, on the laptop, run the 20-day simulation only when prerequisites pass

Complete and test the orchestration on the development PC, then provide the exact laptop command. Run all twenty prepared batches cumulatively using the fixed configuration and daily seed `2026` only after the repository has been synchronized to the laptop and the baseline/one-seed/three-seed gates pass.

For every day, validate the batch, create the cumulative snapshot, train, select the best checkpoint, evaluate on unchanged test and golden sets, package and reload, run mandatory controls, run backend checks where practical, apply the frozen gate, and preserve the report whether accepted or rejected.

Do not silently skip failed days. Represent every failure and reason in the final report.

## Task 11: Run useful ablations only

If resources allow, run:

1. Original data versus corrected labels.
2. Original normal traffic versus expanded normal traffic.
3. Cumulative versus newest-only training.

Run v2 preprocessing only as a separate experiment. Every ablation must state its research question before execution.

## Task 12: Statistical and error analysis

Use paired current-versus-candidate predictions. Report absolute metric differences, per-class/category error changes, confidence intervals where practical, McNemar’s test where appropriate, effect sizes, seed mean/standard deviation, and cumulative daily trends.

Do not treat correlated cumulative days as independent samples. Do not claim statistical significance when sample size or assumptions do not support it.

## Task 13: Package, stage, and verify rollback only with explicit approval

Before staging any candidate, archive and hash the current artifact, record its identity, validate candidate metadata, package and reload the candidate, run backend health and control checks, and confirm the old artifact remains available.

If a critical post-stage check fails, restore the previous artifact, reload the service, verify previous identity and health, and record the rollback reason. Do not claim production deployment; at most, perform explicitly authorized local/staging validation.

# Required laptop handoff

Before ending the coding-agent session, create or update:

```text
docs/project-ops/LAPTOP_TRAINING_HANDOFF.md
```

This handoff must be based on the actual implemented files and commands, not placeholders. It must include:

- Repository branch and commit containing the implementation.
- Whether the branch is merged or still a PR.
- Exact laptop synchronization commands for both cases:

```powershell
# If the PR has been merged into master
git fetch origin
git switch master
git pull --ff-only origin master

# If the PR is still open
git fetch origin
git switch feature/20-day-retraining-simulation
git pull --ff-only origin feature/20-day-retraining-simulation
```

- Laptop virtual-environment setup commands using the repository’s existing dependency files.
- Python, PyTorch, CUDA, GPU, and dataset verification commands.
- Focused test command.
- Tiny smoke command.
- Exact current-model baseline command.
- Exact seed-2026 training command.
- Exact three-seed command.
- Exact 20-day simulation command.
- Exact evaluation/report commands after training.
- Expected output directories and required files.
- Which generated outputs should be copied back to the development PC.
- Which files must not be copied or committed, including private datasets, checkpoints, ordinary logs, and secrets.
- Laptop-specific failure recovery steps.

The handoff must explicitly say that the real full training and 20-day simulation were `NOT_RUN` or `REQUIRES_LAPTOP` if they were not executed in the current session.

The coding agent must ensure that all commands resolve paths from the repository root or configuration and work when the repository path contains spaces. It must not place the PC’s absolute path into tracked configuration or documentation as a required runtime path.

The intended sequence after the coding PR is merged is:

```text
sync laptop repository
→ recreate/activate laptop environment
→ verify GPU and dataset
→ run focused tests
→ run smoke simulation
→ run baseline
→ freeze acceptance thresholds
→ run seed 2026
→ run three-seed confirmation
→ run 20-day cumulative simulation
→ copy back reports/manifests and selected artifact evidence
```

# Frozen acceptance criteria

Before candidate results are inspected, define the actual values in configuration. Start with these proposed gates and revise only with documented, pre-result justification:

- Exact pagination request: `Normal` and `ALLOWED`.
- Every mandatory benign control: expected label and `ALLOWED`.
- Every mandatory attack control: expected attack label and expected non-Normal action.
- Normal false-positive rate: baseline plus no more than `0.001`.
- Attack escape rate: baseline plus no more than `0.001`.
- Macro F1: no decrease greater than `0.002`.
- Normal recall: at least `0.995`.
- Supported-attack class recall: no decrease greater than `0.01`.
- Label mapping unchanged.
- Preprocessing version unchanged for the primary experiment.
- Thresholds unchanged.
- Response-action mapping unchanged.
- Complete run bundle.
- Successful packaging and reload.
- Backend health pass.
- No critical WAF/dashboard smoke regression.

Use `REJECTED` when any mandatory blocker fails. Preserve the candidate and failure evidence.

# Testing requirements

Follow the repository’s existing testing approach and `AGENTS.md` instructions. At minimum, add tests for golden-set loading/hash validation, the exact mandatory benign request, expected label/action checking, invalid batch schema, unverified labels, missing provenance, unknown preprocessing versions, duplicate/conflicting-label rejection, golden overlap, cumulative snapshots, deterministic manifests, incomplete runs, packaging/reload failure, acceptance/rejection gates, and active-model mutation protection.

Use temporary directories and small synthetic fixtures. Tests must not require a GPU, internet download, private data, or developer-specific absolute paths.

Run focused tests first, then relevant existing ML/evaluation/backend tests, the two-day smoke simulation, real candidate reload when available, real-model backend checks when the environment permits, the relevant full suite, and a final machine-specific-path search. Run `git diff --check`. Report every unavailable or skipped check honestly.

# Documentation requirements

Update or create only documentation required by the implementation. Document experiment scope/non-goals, prepared-batch schema, golden-set creation/locking, smoke/baseline/seed/simulation commands, acceptance criteria, artifact/report locations, rollback, limitations, and the difference between controlled simulation and production retraining.

Do not overwrite existing untracked user documents. Do not commit generated checkpoints or private data.

# Final senior-level review

After implementation and tests pass, review the complete diff as a senior reviewer. Check data leakage, golden contamination, unverified-label use, cumulative behavior, preprocessing parity, model/tokenizer identity, label/threshold consistency, path portability, artifact integrity, failure handling, duplicate-job behavior, production-registry protection, sensitive-request handling, mock-versus-real-model coverage, and documentation claims.

If defects or weak decisions are found, fix them through additional focused commits, rerun affected tests, and update the final report. Do not hide failed attempts.

# Required final report

Report the branch and commit list, PR status if created, files created/modified/not changed, repository state, architecture decisions, rejected alternatives, research sources, exact test commands/results, smoke result, baseline result, one-seed result, three-seed result, Day 1–20 results or honest blocked/not-run status, accepted/rejected candidates, exact-request result, false-positive and attack-escape trends, packaging/reload result, backend/WAF/dashboard result by environment, rollback status, security findings, performance observations, reproducibility limitations, remaining risks, and the exact next manual action for the thesis owner.

Also report the laptop handoff document path, exact synchronization commands, exact training commands, expected artifact locations, and which steps are `REQUIRES_LAPTOP`.

Use one final status:

- `SUCCESS`
- `ROLLED_BACK`
- `BLOCKED`
- `RESEARCH_COMPLETE_ONLY`

Do not report `SUCCESS` if the required workflow was not actually executed.

END PROMPT
```
