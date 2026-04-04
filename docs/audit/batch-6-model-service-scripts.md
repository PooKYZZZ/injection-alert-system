# Batch 6 Audit: Model Service And Script-Side Data/Model Changes

## 1. Batch summary

### What this batch is supposed to do
- Extend model artifact loading in runtime model service to support packaged artifact directories and packaged eval report metadata.
- Add script-side tooling to replay labeled attack samples against internal prediction APIs.
- Add fixture data for script replay and add a model config artifact file.
- Preserve architecture boundaries while avoiding runtime/config drift.

### Why this batch is risky
- It touches model artifact resolution and metadata parsing in runtime inference paths, which can break startup, health reporting, or downstream confidence interpretation.
- It introduces a second model service copy in a new location, creating immediate architecture-boundary duplication/drift risk.
- It adds script + fixture behavior that can produce misleading confidence in model quality if defaults/fallbacks are weak.
- It introduces a config artifact in web_app namespace that can be mistaken for runtime config source of truth.

### Main files
- web_app/services/model_service.py
- distillbert/services/model_service.py
- scripts/attack_dataset_tester.py

### Supporting files
- scripts/fixtures/attack_dataset_samples.json
- web_app/config.json

### Tests that are supposed to prove the behavior
- tests/unit/test_model_service.py
  - test_production_requires_explicit_run_directory
  - test_development_broad_path_resolves_latest_run
  - test_explicit_run_directory_does_not_drift
  - test_packaged_artifact_directory_is_accepted
  - test_confidence_tier_boundaries_are_locked
- tests/integration/test_app_startup.py
  - startup behavior with missing artifact in production/testing
  - app.state model service wiring
  - ml-health response includes eval metadata defaults
- tests/integration/test_api.py
  - /api/predict response contract includes class_label/confidence/confidence_level/action_taken

Gap called out up front: no direct tests found for distillbert/services/model_service.py, scripts/attack_dataset_tester.py behavior, scripts fixture freshness, or web_app/config.json usage.

## 2. Files audited
- web_app/services/model_service.py
- distillbert/services/model_service.py
- scripts/attack_dataset_tester.py
- scripts/fixtures/attack_dataset_samples.json
- web_app/config.json
- tests/unit/test_model_service.py (coverage verification)
- tests/integration/test_app_startup.py (coverage verification)
- tests/integration/test_api.py (coverage verification)

## 3. Findings

### Critical
1. Duplicate runtime model service implementation introduces architecture-boundary drift and future divergence risk.
- Evidence:
  - distillbert/services/model_service.py:14 (new second ModelService implementation)
  - distillbert/services/model_service.py:180,299,322 (same new artifact/eval logic surface)
  - web_app/services/model_service.py:14,180,299,322 (equivalent implementation in canonical runtime path)
- Impact:
  - Two sources of truth for model loading behavior in one branch.
  - Any hotfix to one file can silently miss the other and cause inconsistent behavior across tooling/runtime.
- Additional concern:
  - No usage references found to distillbert/services/model_service.py outside planning docs, indicating orphaned but committed logic.

### High
2. Script success criteria can report pass even when model classification quality is bad.
- Evidence:
  - scripts/attack_dataset_tester.py:417 returns success based only on transport success (all HTTP ok), not label-match quality.
  - Label-match is only printed (scripts/attack_dataset_tester.py:333-345 region), not enforced in exit status.
- Impact:
  - CI/operator usage can get false-green outcomes while model quality regresses.
  - Strongly misleading for “attack dataset tester” intent.

3. Silent fallback from explicit missing dataset path to tiny fixture can hide operator mistakes and bias results.
- Evidence:
  - scripts/attack_dataset_tester.py:131-136 falls back to fixture when explicit --dataset path is missing.
  - scripts/attack_dataset_tester.py:18 points fallback to scripts/fixtures/attack_dataset_samples.json.
- Impact:
  - Typos in dataset path do not hard-fail.
  - Script may evaluate on tiny curated fixture instead of intended dataset, producing misleading confidence.

4. Added web_app/config.json creates hidden coupling/confusion with runtime config ownership.
- Evidence:
  - web_app/config.json added as model artifact-style config.
  - Runtime settings source is web_app/config.py (Pydantic Settings), not web_app/config.json.
  - No branch-local runtime references to web_app/config.json were found.
- Impact:
  - Name collision with web_app/config.py increases chance of future mistaken reads/writes.
  - Artifact snapshot in app package path can drift from actual served artifact metadata.

### Medium
5. Model service artifact-directory detection allows broad packaged-directory acceptance with minimal identity checks.
- Evidence:
  - web_app/services/model_service.py:180-188 accepts package directory by manifest OR config.json+tokenizer.json presence.
- Impact:
  - Non-target or stale packaged folders can be accepted as valid candidates until later failure surfaces.
  - Increases startup ambiguity and troubleshooting cost.
- Counterpoint:
  - Production still requires explicit directory selection (web_app/services/model_service.py:147-151 path), reducing accidental broad scans.

6. Default candidate dataset list includes training split, which can leak training data into ad hoc quality checks.
- Evidence:
  - scripts/attack_dataset_tester.py:19-23 candidate order includes train.parquet after test/validation.
- Impact:
  - If test/validation are absent, ad hoc checks may unintentionally report optimistic results from train data.

### Low
7. Script/fixture additions appear untested and likely to rot.
- Evidence:
  - No tests found referencing attack_dataset_tester or attack_dataset_samples in tests/**.
- Impact:
  - Behavior drift and contract drift likely over time (endpoint schema/auth assumptions).

## 4. High-risk files in this batch
- distillbert/services/model_service.py
  - Reason: duplicate implementation of runtime model loading path with no clear ownership or usage.
- scripts/attack_dataset_tester.py
  - Reason: misleading exit criteria and silent dataset fallback can create false confidence.
- web_app/config.json
  - Reason: orphan-like config artifact in runtime package namespace creates hidden coupling and confusion.
- web_app/services/model_service.py
  - Reason: widened artifact acceptance and eval parsing are runtime-critical and can affect startup/health behavior.

## 5. Files that appear disciplined
- tests/unit/test_model_service.py
  - Positive: explicitly validates new packaged artifact acceptance and run-directory selection behavior.
- tests/integration/test_app_startup.py
  - Positive: checks startup fail-fast vs mock fallback behavior and ml-health metadata defaults.
- scripts/fixtures/attack_dataset_samples.json
  - Positive: clear labels and mixed attack/normal records; structure is consistent and parseable.

## 6. Questions or ambiguities needing cross-batch verification
1. Is distillbert/services/model_service.py intentionally a new boundary (package extraction) or an accidental duplicate snapshot? If intentional, where is its owner and import path contract?
2. Should script pass/fail semantics be transport-only, or should labeled match thresholds gate success for audit/quality workflows?
3. Is fallback from explicit missing --dataset intended policy, or should explicit path always fail hard?
4. Why is web_app/config.json stored under runtime app path instead of model artifact registry/export location? Is any deployment process consuming it?
5. Are there branch-level docs declaring scripts/attack_dataset_tester.py as production-adjacent validation, or is it strictly manual ad hoc tooling?
6. Should packaged artifact acceptance require explicit manifest identity fields (model key/version) before being treated as valid?

## 7. Batch verdict
- Verdict: FAIL (merge-blocking for this batch).
- Basis:
  - Critical architecture duplication (second model service source of truth).
  - High-risk script semantics that can produce false-green outcomes.
  - Config artifact placement introduces hidden coupling/confusion without demonstrated runtime use.
- This is a batch-level verdict only, not a final branch merge verdict.
