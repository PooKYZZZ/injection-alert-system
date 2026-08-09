# ML Retraining Pipeline

This directory contains a controlled offline 20-day cumulative retraining
simulation. It is not a production scheduler, queue, online-learning service,
or automatic promotion path. The reusable training entrypoint remains under
`ml_model/training/`.

## Target Purpose
- Manual explicitly invoked retraining trigger
- Analyst-labeled data export
- Dataset validation before training
- Dry-run/smoke mode for orchestration checks
- Real training mode only when explicitly run
- Evaluation report and candidate artifact output
- Manual approval before promotion
- Rollback path if promotion fails

## Implemented controlled experiment

- `experiment_contract.py` loads the immutable v1 TOML contract.
- `validate_batch.py` rejects unapproved, unprovenanced, duplicate, conflicting,
  unknown-label, predicted-label, preprocessing-mismatched, and golden-overlap
  samples while preserving privacy-safe quarantine evidence. It also validates
  model-input hashes and batch-day provenance. Real approved rows require
  reviewer identity and review time; empty batches and synthetic rows marked as
  approved training data are rejected. Checked-in synthetic rows are explicitly
  simulation fixtures and are accepted only with the smoke, test override, or
  explicit controlled-simulation mode.
- `snapshots.py` creates versioned cumulative train snapshots and preserves the
  historical validation/test splits, including the metadata and checksum
  contract required by the training preflight. It builds one reusable index
  over train, validation, and test per simulation, checks exact normalized
  hashes before safe length-bucketed fuzzy candidates. The length bounds use
  the maximum possible `SequenceMatcher` ratio, so valid 85/100-length
  near-duplicates at threshold `0.90` remain candidates. It checks only new
  daily samples against historical and accepted daily records. It rejects
  exact, near-duplicate, duplicate, and conflicting-label contamination and
  records row counts, candidate comparisons, exact/fuzzy matches, rejected
  IDs, and hashes for data, metadata, checksums, historical inputs, and the
  canonical snapshot manifest. The index keeps normalized comparison text and
  raw-input hashes, not a duplicate full raw-text field. Run
  `python -m ml_model.retraining.benchmark_contamination_index --rows 100000
  --queries 10` before native training and record memory and comparison ratio
  against the full-scan baseline; the synthetic benchmark does not prove
  full-dataset fit.
- `request_similarity.py` provides the comparison-only canonicalizer shared by
  golden-overlap and contamination checks. It sorts decoded query key/value
  pairs while preserving blank values and repeated parameters, without
  changing the runtime model-input contract. Different values and paths remain
  distinct, and the configured near-duplicate ratio remains a heuristic.
- `drift.py` records deterministic per-batch request, label, source,
  confidence, query-parameter, and validation-error dimensions.
- `prediction_artifacts.py` writes deterministic, hash-checked baseline and
  candidate per-example artifacts from the locked golden controls. Stable
  sample IDs, dataset/golden/split provenance, the golden manifest hash, and
  the evaluated serving-manifest/checkpoint hash are required. Baseline and
  candidate model hashes are retained separately and are not expected to
  match.
- `statistical_evidence.py` records paired McNemar exact results, absolute
  accuracy difference, paired error counts, and seeded bootstrap confidence
  intervals only when those artifacts are valid and aligned. Missing evidence
  is `NOT_RUN`; malformed or mismatched evidence is `INVALID`; no p-value is
  promoted to a significance claim.
- `integrity.py` blocks a candidate unless its serving manifest, exact-run
  contract, dataset hash, pinned model/tokenizer identity, policy mappings,
  selected checkpoint, and reload/hash identity remain unchanged.
- `simulate_20_day.py` calls the maintained training/evaluation/export seams,
  performs isolated candidate packaging/reload/backend checks, applies frozen
  gates, and records `ACCEPTED`, `REJECTED`, or `NOT_RUN` per day. A requested
  final day includes every preceding cumulative day; partial runs are
  `PARTIAL`, not complete `SUCCESS`.
- `run_baseline.py` evaluates a specifically selected current artifact against
  the locked golden set without silently discovering or modifying staging. A
  baseline is `FROZEN` when required metrics (including security rates), model
  loading, complete golden evaluation, and local reload verification all pass.
  Golden-control failures are retained as baseline evidence; they do not make
  the comparison baseline disappear. Candidate acceptance still requires all
  locked controls to pass. The report records these separate concerns as
  `baseline_gate` and `baseline_quality`. Native packaging also requires
  `summary_metrics.json`, which supplies operational security rates when the
  classification report does not.

The original checked-in route-specific smoke batches remain under
`data/experiments/retraining_20_day_v1/daily_batches/records_search_v1/`.
The fuller route-aware fixture collection is under
`data/experiments/retraining_20_day_v2/daily_batches/records_search_v2/` and is
generated by `ml_model.retraining.generate_batches`. Both collections are
explicitly marked as curated simulation fixtures (`is_synthetic=true`) and are
not treated as reviewed production samples. Use them only with the explicit
`--controlled-simulation` mode. That mode still requires a frozen real
baseline, performs normal snapshot/contamination/package/reload/golden/backend
gates, and labels its final evidence `CONTROLLED_SIMULATION_ONLY`.

### Current golden-control scope

The active experiment contract uses `golden-v2`:

`data/experiments/retraining_20_day_v1/golden/golden-v2/golden_manifest.json`

It contains 28 locked target-route controls for the Land Records Portal search
route, `GET /records/search`, plus one legacy regression control for
`GET /api/users?page=1&limit=10`. The legacy case is retained to detect an old
model regression, but it is not counted as coverage of the Land Records Portal
because that route does not exist in the target application. The immutable
`golden-v1` files remain available as historical evidence and are not the
current experiment input.

The golden cases are offline model controls. They verify model classification,
confidence, and action mapping; they do not prove that a request passed through
Cloudflare, ModSecurity, the audit bridge, or the live portal. That live path
requires a separate authorized Docker/Cloudflare smoke test.

The `--smoke` mode uses tiny synthetic data and injected adapters to prove
orchestration startup and failure safety. It reports `SMOKE_SUCCESS`,
`real_training_status=NOT_RUN`, `model_quality_conclusion=NOT_PERMITTED`, and
`baseline_status=SMOKE_SYNTHETIC`; its statistical evidence is `NOT_RUN` and
it is not a model-quality or thesis result. The synthetic fixture is not
production data.

The real baseline, corrected one-seed run, three-seed confirmation, and full
20-day native simulation remain `REQUIRES_LAPTOP` unless their artifacts and
reports are freshly generated and inspected.

The v1 acceptance tolerances are locked in code: normal false-positive and
attack-escape increases may each be at most `0.001`, macro-F1 may drop by at
most `0.002`, normal recall must remain at least `0.995`, and supported attack
recall may drop by at most `0.01`. Editing the TOML values cannot weaken these
gates.

## Validation commands and evidence boundaries

From the repository root, run the complete synthetic smoke with all days:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --output-dir ml_model/results/retraining_20_day_v1/smoke `
  --smoke `
  --days 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
```

Before native training, measure the contamination index with representative
synthetic scale:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.benchmark_contamination_index `
  --rows 100000 `
  --queries 10
```

Capture `peak_memory_mib`, `retained_memory_mib`, build/query time, and
`candidate_comparisons_checked` plus `candidate_comparison_ratio`. This does
not modify the real dataset and is not a substitute for validating the actual
laptop's full-dataset memory headroom.

For native execution, first create a baseline artifact and its paired
prediction artifact, then run the simulator with reviewed non-synthetic daily
batches:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.run_baseline `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --artifact-dir ml_model/model_registry/staging/<frozen-run> `
  --output ml_model/results/retraining_20_day_v1/baseline.json

.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v1/daily_batches/records_search_v1 `
  --output-dir ml_model/results/retraining_20_day_v1/native `
  --baseline ml_model/results/retraining_20_day_v1/baseline.json `
  --controlled-simulation `
  --days 1
```

The `--controlled-simulation` option is deliberately explicit. It permits the
prepared fixtures for the thesis simulation; it must not be used to disguise
synthetic data as real reviewed production data. Omit it when using a reviewed
non-synthetic batch export. The v2 fixture generator creates 600 rows across
20 days (400 Normal, 67 SQL Injection, 67 Code Injection, and 66 Other
Attacks), all scoped to the actual `/records/search` route. This improves the
coverage of the controlled experiment, but it does not make the samples real
production observations or prove model improvement by itself.

Then, only after the one-seed and three-seed prerequisites pass, run days 1
through 20 using the same baseline, dataset version, prepared route-specific
batches, and locked golden set. Real training still must be performed on the
laptop. No smoke run, aggregate metric, or present p-value is evidence that
the model improved on production traffic; controlled-fixture results must keep
their simulation-only evidence label.

## Architectural Role
Closes the feedback loop:
  Analyst corrections → reviewed-sample export → data/staging/ → retrain → validate → ml_model/model_registry/

Planned safe flow:

```text
Analyst corrections -> labeled export -> dataset validation -> dry-run or real training
-> evaluation report -> candidate artifact -> manual approval -> promotion -> rollback if needed
```

Existing promotion/rollback tooling lives under `ml_model/export/`; it is not the same thing as a complete retraining pipeline.

## Verified label review input

The web application now records immutable, per-alert review revisions in
`traffic_label_reviews`. The canonical verified-label classes are `SQL
Injection`, `Code Injection`, `Other Attacks`, and `Normal`; this vocabulary is
separate from triage transport status and confidence tier. A future exporter
must select only the latest review with `approval_state=approved_for_training`.
Reviews marked `excluded_from_training` must remain excluded, and superseded
history must not be exported as a second sample.

Reviewer identity is derived from the authenticated server session. New v2
inference rows persist the exact sanitized model-input text, its
`model_input_hash`, and `preprocessing_version`; WAF query strings and
sanitized bodies use the same canonical input before inference. Sensitive
fields are redacted while safe injection indicators are retained as explicit
tokens for classification. The supported legacy v1 artifact keeps its exact
inference behavior but persists only the model-input hash, so those rows are
not eligible for approved training until a redacted v2 artifact is deployed.
Historical rows with missing text/provenance remain readable but are not
eligible for approved training. The exporter is still not implemented, so
automated or source-equivalent training data remains `Planned`.

This workflow does not provide a scheduler, daily production retraining
operation, blind promotion, automatic rollback, or production model-registry
mutation. Any training and promotion remains an explicit, manually reviewed
operation. See `docs/project-ops/LAPTOP_TRAINING_HANDOFF.md` for the exact
operator sequence.
