# Controlled offline 20-day retraining experiment

## Scope and claim boundary

This implementation runs a controlled offline 20-day retraining simulation
using prepared and verified daily batches. The batches may be curated or
synthetic; they do not represent twenty calendar days of reviewed production
traffic. The result must therefore be described as a controlled simulation,
not production daily retraining.

The primary research question is whether cumulative replay of reviewed benign
and attack examples reduces the benign false positive for
`GET /api/users?page=1&limit=10` without increasing attack escapes, changing
the confidence/action contract, or breaking packaging and backend loading.

There is no scheduler, queue, database migration, dashboard training button,
online learning from predictions, automatic staging replacement, production
promotion, or production-registry write.

## Frozen protocol

The source of truth is
`ml_model/configs/retraining_20_day_v1.toml`. It freezes:

- historical dataset `v3_907k_cleaned`;
- primary preprocessing `http-preprocessor-v1`;
- native `distilbert-base-uncased` at revision
  `12040accade4e8a0f71eabdb258fecc2e7e948be`;
- daily seed `2026`, confirmation seeds `42`, `1337`, and `2026`;
- maximum four epochs;
- `golden-v1`, the label order, confidence thresholds, and
  `ALLOWED`/`THROTTLED`/`BLOCKED` mapping;
- pre-result acceptance tolerances.

The exact pagination request is locked in the golden set and is not present in
the prepared training batches. Daily snapshots append only validated samples
to the historical training split; validation, test, and golden controls stay
unchanged. Every generated snapshot also contains the shared preprocessing
metadata and checksum manifest accepted by the maintained training preflight.

## Data controls

Every prepared JSONL row contains:

`sample_id`, `model_input_text`, `model_input_hash`, `ground_truth_label`,
`batch_day`, `source_type`, `is_synthetic`, `review_status`, `provenance_id`,
and `preprocessing_version`.

Real training rows require `review_status=approved_for_training`, reviewer
identity, and review time. The checked-in daily files instead use
`review_status=curated_simulation_fixture`, `source_type=curated_simulation_fixture`,
and `is_synthetic=true`; normal training-mode validation rejects them. Only
the explicit smoke/test override accepts these fixtures, and that override
cannot produce a real model-quality conclusion. The validator rejects unknown
labels, missing ground truth, any model-prediction label field, unapproved or
synthetic rows in real mode, missing provenance, mismatched preprocessing,
duplicates, conflicting labels, exact or near-duplicate historical overlap,
missing or invalid model-input hashes, and wrong batch-day provenance.
Rejected rows remain in a deterministic privacy-safe quarantine JSONL report
containing only identifiers, source type, and a request-text hash; raw request
text is not stored.

### Historical contamination index

`snapshots.py` builds one `ContaminationIndex` per simulation from all three
historical splits. The index stores the existing canonical request
normalization, deterministic query-parameter ordering, an exact normalized
text hash, and normalized-length buckets. An exact-hash lookup runs first.
Non-exact candidates are limited only by the mathematically safe normalized
length range before the existing `SequenceMatcher` threshold (`0.90`); method
and parsed path are deliberately not used as exclusion filters.
This avoids a cumulative-day-by-full-history scan without silently dropping
near duplicates whose method or path changed.

Each new day is checked once against the historical index and the accepted
daily index, including within-day duplicate/conflicting-label checks and
cross-day exact/near-duplicate checks. Only a validated day is then added to
the daily index. Reports include historical and daily row counts, candidate
comparisons, exact and fuzzy match counts, and rejected sample IDs. The
length/hash index cannot determine semantic equivalence and the near-duplicate
ratio remains a heuristic; it must not be described as a complete semantic
deduplication proof.

## Orchestration and evidence

For each simulated day the orchestrator validates the batch, builds a
versioned cumulative snapshot, validates all runtime inputs and the historical
dataset contract before creating output, invokes `ml_model.training.train`,
validates the run bundle through `ml_model.evaluation.evaluate`, packages into
an isolated candidate registry through the existing export boundary,
reload-tests the candidate, runs golden controls and the direct `ModelService`
backend boundary using the contract policy, and applies the gates. A failed
day is recorded as `REJECTED` with its stage and error; later cumulative days
are recorded `NOT_RUN` and cannot produce accepted candidates. Normal callers
cannot bypass the locked golden set or write inside the model registry. No
active registry path is used as an output target.

The backend evidence is intentionally limited to the direct `ModelService`
boundary. FastAPI route integration, Next.js/BFF behavior, WAF enforcement,
dashboard behavior, hosted deployment, and production traffic are not run by
this experiment and remain separate evidence obligations.

The snapshot manifest records parquet hashes, the preprocessing metadata hash,
the checksum-file hash, the historical input file hashes, and canonical
manifest hashes. The candidate contract gate then verifies that the serving
manifest and exact-run contract preserve labels, preprocessing, model and
tokenizer revision, thresholds, action mapping, dataset hash, selected best
checkpoint, and artifact identity. Every day also records deterministic batch
drift dimensions.

The aggregate run-bundle evaluator does not provide paired per-example
predictions, so the simulator uses the locked golden-control evaluation as its
comparison set. `run_baseline.py` writes the frozen
`baseline_predictions.json`; each native candidate writes a corresponding
candidate artifact. Each row contains `sample_id`, `split`, `y_true`,
`prediction`, confidence, confidence tier, response action, model version,
dataset version, and golden version. The artifacts are hashed and joined by
stable `sample_id` only when the dataset, golden set, split, and comparison-set
hash agree.

Evidence is `COMPUTED` only for a valid pair and includes McNemar's exact test,
absolute accuracy difference, baseline-only/candidate-only/both-correct/
both-wrong counts, and a seeded bootstrap confidence interval. `NOT_RUN` means
the pair is unavailable (including smoke); `INVALID` means malformed or
mismatched inputs. A p-value is not treated as a significance claim, and the
locked comparison set is not by itself thesis-quality evidence. Native
acceptance requires `COMPUTED`; smoke remains explicitly non-thesis evidence.

The synthetic smoke result is reported as `SMOKE_SUCCESS`, with
`real_training_status=NOT_RUN`, `model_quality_conclusion=NOT_PERMITTED`, and
`baseline_status=SMOKE_SYNTHETIC`. The synthetic fixture must not be treated as
production data or as evidence that a model improved. Real native training on
the laptop, with the historical dataset, prepared reviewed batches, frozen
baseline, candidate artifacts, reload, and acceptance gates, remains required.

## Engineering and research basis

The controls are intentionally conservative and use the repository’s existing
training seams. The design is informed by the NIST AI Risk Management
Framework, NIST Secure Software Development Framework, OWASP Machine Learning
Top 10, PyTorch reproducibility guidance, Hugging Face trainer callbacks,
scikit-learn model evaluation and group-aware validation guidance, staged
promotion/rollback guidance from AWS, Guo et al. on calibration, Dietterich
on paired classifier tests, Kirkpatrick et al. on catastrophic forgetting,
and replay-based intrusion-detection research. Practitioner discussions are
treated as anecdotal engineering input only. No infrastructure or continual-
learning dependency is introduced on that basis.

- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST SSDF](https://csrc.nist.gov/projects/ssdf)
- [OWASP ML Top 10](https://owasp.org/www-project-machine-learning-security-top-10/)
- [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)
- [Hugging Face Trainer callbacks](https://huggingface.co/docs/transformers/main/trainer_callbacks)
- [scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [AWS staged deployment guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/continuous-deployment.html)
- [Guo et al. calibration](https://proceedings.mlr.press/v70/guo17a.html)
- [Dietterich paired classifier tests](https://pubmed.ncbi.nlm.nih.gov/9744903/)
- [Kirkpatrick et al. catastrophic forgetting](https://doi.org/10.1073/PNAS.1611835114)
- [Replay and intrusion detection](https://doi.org/10.1109/MILCOM64451.2025.11310341)

## Acceptance gates

Before inspecting candidate results, the TOML freezes these gates:

- exact pagination: `Normal` and `ALLOWED`;
- all locked benign/attack controls pass their expected label and action;
- normal false-positive rate is no more than baseline + `0.001`;
- attack escape rate is no more than baseline + `0.001`;
- macro F1 does not decrease by more than `0.002`;
- normal recall is at least `0.995`;
- supported attack recall does not decrease by more than `0.01`;
- every supported attack class is present in the frozen baseline recall;
- preprocessing, labels, thresholds, run-bundle completeness, packaging,
  reload, and backend checks remain valid;
- candidate contract integrity is explicitly `passed`.

Missing baseline metrics are `Unknown`/`REQUIRES_LAPTOP`; they are never
replaced with guessed zeros. A candidate that misses a mandatory gate is
preserved and marked `REJECTED`. A one- or two-day normal run is `PARTIAL`,
not the complete experiment `SUCCESS`.

## Reproducibility and limitations

Input and output hashes, distributions, run paths, and per-day status are
recorded. PyTorch/Hugging Face reproducibility remains hardware- and
environment-dependent even with fixed seeds. Prepared synthetic batches,
small golden controls, and direct backend checks do not prove production
readiness, hosted WAF enforcement, dashboard behavior, or real-world drift
coverage.
