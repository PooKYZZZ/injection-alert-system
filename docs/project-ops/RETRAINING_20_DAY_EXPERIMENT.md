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
unchanged.

## Data controls

Every prepared JSONL row contains:

`sample_id`, `model_input_text`, `ground_truth_label`, `batch_day`,
`source_type`, `is_synthetic`, `review_status`, `provenance_id`, and
`preprocessing_version`.

Only `review_status=approved_for_training` is eligible. The validator rejects
unknown labels, missing ground truth, any model-prediction label field,
unapproved rows, missing provenance, mismatched preprocessing, duplicates,
conflicting labels, and exact golden overlap. Rejected rows remain in a
deterministic quarantine JSONL report.

## Orchestration and evidence

For each simulated day the orchestrator validates the batch, builds a
versioned cumulative snapshot, invokes `ml_model.training.train`, validates
the run bundle through `ml_model.evaluation.evaluate`, packages into an
isolated candidate registry through the existing export boundary, reload-tests
the candidate, runs golden controls and the direct `ModelService` backend
boundary, and applies the gates. A failed day is recorded as `REJECTED` with
its stage and error; it is never silently skipped. No active registry path is
used as an output target.

The smoke result proves orchestration and failure safety only. It does not
support claims about accuracy or retraining quality.

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
- preprocessing, labels, thresholds, run-bundle completeness, packaging,
  reload, and backend checks remain valid.

Missing baseline metrics are `Unknown`/`REQUIRES_LAPTOP`; they are never
replaced with guessed zeros. A candidate that misses a mandatory gate is
preserved and marked `REJECTED`.

## Reproducibility and limitations

Input and output hashes, distributions, run paths, and per-day status are
recorded. PyTorch/Hugging Face reproducibility remains hardware- and
environment-dependent even with fixed seeds. Prepared synthetic batches,
small golden controls, and direct backend checks do not prove production
readiness, hosted WAF enforcement, dashboard behavior, or real-world drift
coverage.
