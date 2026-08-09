# Daily Retraining Journal

## Goal

Build a safe, thesis-scale retraining workflow for the injection-alert model.

The intended flow is:

```text
Reviewed alert -> approved training sample -> versioned dataset -> candidate model
-> evaluation against active model -> PROMOTE, HOLD, or REJECT -> manual promotion
```

This is not yet a daily automated pipeline. Do not claim that it is until every
required item below is complete and tested.

## What already exists

- [x] Script-first DistilBERT training entrypoint: `ml_model/training/train.py`.
- [x] Training evaluation output: `ml_model/evaluation/evaluate.py`.
- [x] Portable laptop training configuration and smoke/benchmark support.
- [x] Alert storage records prediction, confidence, confidence tier, timestamp,
  action, and model version.
- [x] Alert rows contain `analyst_label`, `labeled_by`, and `labeled_at` fields.
- [x] Backend feedback endpoint exists: `POST /api/feedback`.
- [x] Dashboard supports triage statuses such as Resolve and False Positive.
- [x] Candidate packaging, archive, and rollback foundations exist under
  `ml_model/export/`.

## What is still missing

- [ ] A dashboard control for selecting a verified canonical model label.
- [ ] Backend validation that allows only the canonical model labels.
- [ ] Reviewer identity derived from the authenticated account.
- [ ] Immutable review history instead of replacing the prior label.
- [ ] Explicit `approved_for_training` state.
- [ ] Approved-sample export to the model dataset format:
  `combined_payload` and `final_label`.
- [ ] A safe policy for the model-input text used in retraining. Dashboard
  evidence is sanitized/redacted, so it may not be identical to inference input.
- [ ] Dataset manifest, hashes, version, and export/consumption tracking.
- [ ] Candidate evaluation against the selected active model.
- [ ] Recorded PROMOTE / HOLD / REJECT decision with reasons.
- [ ] Safe active-model replacement and reload/restart validation.
- [ ] Retraining run history for the dashboard or reports.
- [ ] One-run lock, failure recovery, and optional daily scheduler.

## Work in order

### Step 0 — Finish the current baseline run

Status: **Complete and verified as the controlled baseline**

- [x] Let the current three-seed DistilBERT run finish.
- [x] Run the existing evaluation command for its output folder.
- [x] Record the mean and variation across seeds.
- [x] Select and document one baseline artifact before any retraining study.

The terminal output, laptop run metadata, checkpoint inventory, canonical
dataset audit, and cross-machine dataset hashes confirm that training and
aggregation completed on the intended dataset. The run is the controlled
baseline for the next retraining experiment.

Baseline run:
`v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260802_155314`

Configuration source: `laptop_cuda_distilbert.toml`/the generated recommended
configuration, with command-line overrides. Effective configuration: DistilBERT,
weighted cross-entropy, dataset `v3_907k_cleaned`, seeds `42`, `1337`, and
`2026`, four maximum epochs, CUDA FP16 laptop run, batch size 64, evaluation
batch size 128, zero data-loader workers, sequence length 128, and gradient
accumulation 2. The TOML itself still lists seed `42` and five epochs; the
three-seed command explicitly overrode those values.

Artifact evidence: each seed has a best checkpoint of approximately 266 MB and
a last checkpoint of approximately 799 MB. The run manifest reports no failed
seeds, and the evaluation aggregation reports three seed summaries.

Three-seed mean results:

| Metric | Mean |
|---|---:|
| Validation macro F1 | 0.993629 |
| Test accuracy | 0.992600 |
| Test balanced accuracy | 0.994711 |
| Test macro F1 | 0.988732 |
| Normal false-positive rate | 0.002825 (0.2825%) |
| Attack escape rate | 0.002082 (0.2082%) |
| Calibrated test ECE | 0.004217 |
| Calibrated test Brier score | 0.010044 |
| Mean inference latency | 9.212 ms |

Seed stability observations:

- Test accuracy ranged from 0.992515 to 0.992720.
- Test macro F1 ranged from 0.988671 to 0.988842.
- Normal false-positive rate ranged from 0.002460 to 0.003280.
- Attack escape rate ranged from 0.001830 to 0.002272.

Interpretation: the three seeds are close enough to use this run as the
controlled baseline candidate. The inspected manifest confirms the expected
four labels, three seeds, zero measured cross-split overlap, and no failures.
The canonical dataset directory separately contains the upstream cleaning
audit, so those provenance details are recoverable even though the run manifest
did not link them. These are held-out dataset results, not proof of production
or zero-day performance.

Recovered dataset provenance from `data/processed/v3_907k_cleaned/`:

- Pipeline version `3.1.0`, source-cleaning commit
  `339883bf3efcc3799fbccb9a4c2947ae0661950d`.
- 907,815 initial rows; 2 malformed rows removed; 544,760 exact duplicates
  removed.
- 23,826 suspicious benign rows quarantined.
- MinHash near-duplicate analysis used shingle size 5, threshold 0.85, and
  128 permutations; cluster cap was 100 samples.
- Final dataset size was 199,039 rows with 159,873 train, 19,661 validation,
  and 19,505 test rows.
- Exact-hash and cluster-overlap checks across splits both passed with zero
  overlap; the audit also reports a zero-similarity 5,000-row near-duplicate
  sample check.
- Canonical split checksums are recorded in `checksums.txt`; the laptop copy
  were compared against the laptop copy and matched exactly for train,
  validation, and test Parquet files.

### Step 1 — Design the verified-label workflow

Status: **Not started**

- [ ] Decide the exact canonical labels shown to reviewers.
- [ ] Define what `False Positive` means for training (normally `Normal`).
- [ ] Define who can label, approve, or reject a sample.
- [ ] Define when a reviewed label becomes approved for training.
- [ ] Decide the retention/privacy policy for training-safe model input.

Done when: the label lifecycle is written down and matches the model's four
classes.

### Step 2 — Implement review and approval

Status: **Not started**

- [ ] Add the dashboard review control.
- [ ] Add the BFF route; preserve Browser -> Next.js BFF -> FastAPI.
- [ ] Validate labels in the backend.
- [ ] Use authenticated reviewer identity.
- [ ] Store review history and approval state.
- [ ] Add focused backend and frontend tests.

Done when: an authorized reviewer can approve one alert with a valid label and
an audit trail is preserved.

### Step 3 — Export a retraining dataset

Status: **Not started**

- [ ] Export only approved, unconsumed samples.
- [ ] Reuse the inference-compatible preprocessing contract.
- [ ] Reject invalid labels, duplicates, empty input, and unsafe records.
- [ ] Create train/probe partitions before training.
- [ ] Keep related scenario families out of both partitions.
- [ ] Write a dataset manifest with counts, labels, hashes, and source IDs.

Done when: the exported dataset can be loaded by `ml_model/training/train.py`
without manual editing.

### Step 4 — Train one candidate manually

Status: **Not started**

- [ ] Mix approved new samples with a frozen replay dataset.
- [ ] Use the existing portable training command.
- [ ] Save all run configuration, seed, checkpoint, and metrics.
- [ ] Keep the candidate outside the active production model path.

Done when: the candidate model trains from the exported dataset and produces a
separate run folder.

### Step 5 — Evaluate and decide

Status: **Not started**

- [ ] Compare active and candidate on the same held-out data.
- [ ] Measure per-class precision, recall, F1, and confusion matrix.
- [ ] Calculate true Normal false-positive rate from ground-truth labels.
- [ ] Check attack recall does not regress beyond the agreed threshold.
- [ ] Record one decision: PROMOTE, HOLD, or REJECT.

Done when: a candidate cannot become active without a recorded evaluation and
decision.

### Step 6 — Package, promote, and recover

Status: **Not started**

- [ ] Package a passing candidate with version and provenance metadata.
- [ ] Test loading it in the application staging/local environment.
- [ ] Keep the previous active artifact recoverable.
- [ ] Verify rollback after a deliberate failed load test.

Done when: a manual promotion can be reversed safely.

### Step 7 — Add automation last

Status: **Deferred until Steps 1-6 work manually**

- [ ] Add a one-run lock.
- [ ] Add idempotent run IDs and safe retry behavior.
- [ ] Schedule a daily check, not blind daily promotion.
- [ ] Skip safely when there are too few approved samples.
- [ ] Log start, dataset version, result, decision, and failure reason.

Done when: the scheduler runs the already-proven manual pipeline without
creating duplicate runs or automatically deploying an unapproved model.

## Do not do yet

- [ ] Do not train from every incoming alert.
- [ ] Do not treat model predictions as ground truth labels.
- [ ] Do not use dashboard triage status alone as a training label.
- [ ] Do not replace `ml_model/model_registry/production/` automatically.
- [ ] Do not claim real-world or zero-day detection from a controlled study.
- [ ] Do not add the scheduler before one manual candidate cycle succeeds.

## Final presentation checklist

- [ ] Show one reviewed alert and its verified label.
- [ ] Show the generated versioned dataset manifest.
- [ ] Show a candidate training run and evaluation report.
- [ ] Show active-versus-candidate comparison.
- [ ] Show one PROMOTE, HOLD, or REJECT decision.
- [ ] Show artifact version and rollback evidence.
- [ ] State clearly whether the final trigger is manual or scheduled.

## Next action

**Use this verified baseline for the next retraining design.**

The next implementation target is the label contract and approval lifecycle,
not the daily scheduler. The original cleaning and split evidence is available
in the canonical dataset audit and should remain linked in future reports.
