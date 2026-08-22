# Dashboard-Triggered Native Laptop Training Implementation Guide

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this guide task-by-task. The repository forbids subagents, so execute inline with review checkpoints. Use TDD for behavior changes and keep each checkbox tied to observable evidence.

**Goal:** Connect the existing Model Operations dashboard to a controlled native training run on the laptop without weakening the repository's evidence, provenance, security, approval, deployment, or accessibility boundaries.

**Architecture:** Preserve Browser → Next.js BFF → FastAPI → durable local run → isolated worker subprocess → native training/evaluation/package path. The browser requests a run and observes state; it never chooses a command, path, dataset, model, or training flag. The active model remains unchanged until an administrator explicitly approves and deploys a verified candidate.

**Tech Stack:** Python 3.14, FastAPI, async SQLAlchemy, Pydantic, the existing ml_model.training entrypoint, PyTorch, Hugging Face Transformers, Docker Compose, Next.js App Router, React, TanStack Query, Zod, Vitest, Testing Library, pytest, PowerShell, and the repository's local filesystem run/artifact contracts.

---

## 1. How to use this guide

This document is the working reference for the implementation agent. Keep it open while coding and update the execution checkboxes only when the corresponding behavior has actually been inspected or validated.

The guide is intentionally narrower than a general MLOps platform design. It describes the smallest complete feature for the repository's current operational model: one local laptop, one controlled worker path, filesystem-backed run state, explicit human review, and explicit local staging.

### Source-of-truth order

Use this order whenever the guide, a prior review, or an assumption conflicts with the checkout:

1. Live source code and runtime behavior.
2. Existing tests, manifests, artifacts, and persisted contracts.
3. AGENTS.md and repository documentation.
4. This guide and the earlier Model Operations plan.
5. Official framework, library, platform, and web-standard documentation.
6. Reputable engineering articles, published research, and design-system guidance.
7. Developer-community discussions as supplementary, low-confidence evidence only.

Do not assume a file, function, dataset version, artifact format, or behavior exists because a document mentions it. Inspect the current owner before editing.

### Evidence labels

Use these labels in implementation notes, test reports, and handoffs:

- IMPLEMENTED — present in live code.
- CONFIRMED_BY_TEST — demonstrated by an executed automated test.
- CONFIRMED_BY_CODE_TRACE — established from live source, but not separately executed.
- MANUALLY_VERIFIED — exercised through the local dashboard/runtime.
- NOT_RUN — not attempted.
- BLOCKED — could not run because of a documented environment or permission issue.
- UNKNOWN — the repository does not establish the fact.

Never convert a smoke result, file existence, or local-only check into a claim of model quality, hosted readiness, or production deployment.

### Working rules

- Inspect the owning implementation and nearby tests before each slice.
- Preserve unrelated working-tree changes.
- Never read, print, hardcode, or commit secrets.
- Do not modify the frozen processed dataset.
- Do not commit generated checkpoints, run results, caches, logs, or private datasets.
- Do not change thresholds, label policy, BLOCKED/THROTTLED/ALLOWED behavior, or deployment policy as part of this feature.
- Do not add a dependency, migration, schema, CI workflow, or infrastructure service without first proving the existing architecture cannot satisfy the requirement and escalating that boundary.

---

## 2. Current state and the actual problem

### What already exists

The repository already has most of the control plane needed for a safe local workflow:

- [ml_model/retraining/dashboard_contracts.py](../../../ml_model/retraining/dashboard_contracts.py) defines typed run states, evidence statuses, artifact allowlists, and binding requirements.
- [ml_model/retraining/dashboard_worker.py](../../../ml_model/retraining/dashboard_worker.py) claims durable runs, holds a worker lock, refreshes heartbeats, enforces timeouts, isolates the pipeline subprocess, and maps failures to bounded states.
- [web_app/infrastructure/retraining_process_runner.py](../../../web_app/infrastructure/retraining_process_runner.py) launches only the allowlisted worker module with an explicit argument list, shell=False, restricted environment, and detached process handling.
- [web_app/presentation/dependencies/retraining.py](../../../web_app/presentation/dependencies/retraining.py) wires the application control plane to the local artifact repository and selects smoke or native execution from the server-only `RETRAINING_WORKER_MODE` setting; smoke remains the default.
- [frontend/features/ml-model/queries.ts](../../../frontend/features/ml-model/queries.ts) polls active run state and stops polling terminal runs.
- [frontend/components/ml-model/MLModelWorkspace.tsx](../../../frontend/components/ml-model/MLModelWorkspace.tsx) renders run state, evidence, decisions, and explicit staging actions through the BFF.
- [docs/project-ops/ML_MODEL_OPERATIONS_RUNBOOK.md](../../project-ops/ML_MODEL_OPERATIONS_RUNBOOK.md) documents the local review, approval, staging, rollback, and recovery boundary.
- [ml_model/training/train.py](../../../ml_model/training/train.py) and the existing training configurations provide the canonical script-first native training path.
- [requirements.train.txt](../../../requirements.train.txt) contains training-only dependencies, but the default runtime image does not install them. Compose exposes the existing `INSTALL_TRAINING_REQUIREMENTS` build argument, which remains `false` unless a native image is intentionally built.

### What the current dashboard does

The default path remains intentionally a controlled smoke path:

~~~
Request retraining
  → durable run
  → SmokeDashboardPipeline
  → CONTROLLED_SMOKE stage artifacts
  → NOT_RUN training/evaluation evidence
  → NOT_ENOUGH_EVIDENCE
~~~

In dashboard_pipeline.py, SmokeDashboardPipeline publishes inspectable stage artifacts without making a native quality claim. NativeDashboardPipeline is available when the server-side setting is `RETRAINING_WORKER_MODE=native`; the browser cannot choose that mode. Native execution also requires the pinned training dependencies from `requirements.train.txt` and the prepared `v3_907k_cleaned_model_input_v2` dataset with its checksums manifest. The default smoke path binds only to the existing `v3_907k_cleaned` dataset identity and does not require the optional v2 dataset. Ordinary CI and non-training environments therefore do not start native training accidentally.

The native path is still a controlled local capability, not a production-training claim. It is not a reason to replace the filesystem worker with a distributed job platform.

### Manual training versus dashboard training

Manual training is useful as an interim runtime diagnostic:

~~~
export a validated dataset snapshot
  → run the existing training entrypoint manually
  → inspect the run directory
~~~

It does not prove that the dashboard can:

- bind the run to the exported snapshot;
- carry the same dataset and preprocessing identity into evaluation;
- record the worker heartbeat and state transitions;
- package the candidate through the shared provenance path;
- expose the candidate for review;
- prevent active-model mutation.

The intended final behavior is one controlled dashboard-triggered run. Manual training must remain a validation tool, not a second maintained production-like workflow.

---

## 3. Target behavior and definition of done

### Successful native run

The normal successful flow must be:

~~~
Browser
  → Next.js BFF request
  → FastAPI accepts and returns a run reference
  → durable QUEUED run
  → worker claims run
  → validated approved-sample export
  → immutable cumulative dataset snapshot
  → native training subprocess
  → evaluation on the established frozen evaluation split
  → active-versus-candidate comparison
  → shared artifact/provenance finalization
  → PENDING_APPROVAL
~~~

The UI must show the run stage, safe status, heartbeat age, dataset identity, candidate identity when available, and evidence status. It must not show invented metrics or claim that the model is active.

### State behavior

The native path should use the existing state machine and preserve its meanings:

~~~
QUEUED
  → EXPORTING
  → DATASET_VALIDATED
  → TRAINING
  → EVALUATING
  → PENDING_APPROVAL
~~~

Failure paths must remain explicit:

- missing or invalid approved data → SKIPPED_NO_APPROVED_DATA;
- transient worker/process failure → retryable failure under the existing retry budget;
- invalid artifact, provenance, or evaluation evidence → terminal failure or NOT_ENOUGH_EVIDENCE as owned by the existing contract;
- timeout or stale heartbeat → existing recovery/retry behavior;
- candidate hold or rejection → active model unchanged;
- candidate approval → approval state only, not activation;
- deployment → a separate explicit local staging action.

Do not add a new state merely because a message would be more convenient. Extend the existing typed contract only if the current states cannot truthfully represent a required native condition.

### Completion gate

The feature is not complete until all of these are true:

- A dashboard request launches the native training path on the configured laptop runtime.
- The browser remains limited to the BFF contract.
- The worker remains outside the FastAPI request lifecycle.
- The run uses an immutable, validated dataset snapshot.
- Dataset, preprocessing, model, configuration, code, and evaluation identities remain bound.
- Native evaluation runs against the established evaluation/holdout contract.
- The candidate is packaged and verified through existing shared logic.
- PENDING_APPROVAL is impossible without complete native evidence.
- The active model is unchanged after training, evaluation, hold, rejection, and failed candidate creation.
- The dashboard reports native versus smoke evidence truthfully.
- Focused backend, frontend, container, and local dashboard validation have been classified accurately.

---

## 4. Hard invariants

These are system properties, not suggestions.

### Data and labels

- verified_label is the training/evaluation ground truth.
- false_positive is a triage relationship, not a training class.
- The operational dashboard proxy is not the true ground-truth false-positive rate.
- Newly approved samples are training inputs; they do not replace the frozen holdout.
- Approved samples remain reusable after a candidate is held or rejected.
- Unknown labels, missing review identity, invalid evidence, and ambiguous preprocessing metadata fail closed.
- The frozen processed dataset is not modified or regenerated by this feature.

### Provenance and integrity

- The source training summary is captured once per promotion/evaluation flow where the existing contract requires a source snapshot.
- A candidate is bound to the dataset snapshot, preprocessing version, training configuration, active-model identity, evaluation split, and artifact digests that were actually reviewed.
- summary_metrics.json integrity is verified through the existing external digest anchor/finalization path.
- The implementation must call shared packaging/provenance finalization rather than duplicating digest logic in the worker or UI.
- Verification fails closed; it never silently falls back to unverified metrics.
- A held or rejected candidate cannot alter the active model.

### Worker and process safety

- The browser cannot select shell commands, executable paths, model paths, output paths, training flags, or arbitrary environment variables.
- Native training runs through the existing isolated worker/process boundary.
- Subprocess invocation uses an explicit argument list and shell=False.
- Timeouts, heartbeats, locks, retries, and stale-run recovery retain their current semantics.
- Worker errors exposed to the API/UI are bounded safe codes/messages, not raw tracebacks, request payloads, filesystem paths, or secrets.
- A worker restart must leave a truthful durable state and inspectable run artifacts.

### Model lifecycle

- Training produces a candidate; it does not activate it.
- Evaluation produces evidence; it does not approve the candidate.
- Approval produces a decision; it does not deploy the candidate.
- Deployment remains explicit, local, staged, load-verified, and rollback-capable.
- The web application does not write to ml_model/model_registry/production/.


---

## 5. Research and uncertainty protocol

Research is part of implementation, not a one-time preface. If an agent becomes uncertain about a browser behavior, framework API, serialization rule, accessibility pattern, responsive layout, state-management behavior, subprocess behavior, or test strategy, pause at that boundary and verify it before coding around the uncertainty.

### Required research sequence

1. State the concrete question.
2. Inspect the repository's current usage and tests.
3. Check official documentation or a recognized standard.
4. Check a primary source, specification, or published research source when applicable.
5. Use reputable engineering guidance or design-system documentation for practical trade-offs.
6. Use recent developer/community discussions only to discover edge cases or operational experience, not as normative authority.
7. Record the conclusion, confidence, source links, and repository-specific decision in the implementation notes or PR description.

Do not browse merely to collect generic best practices. Research must answer a specific uncertainty that could change the implementation.

### Current research baseline

These sources informed this guide and should be revisited if the agent changes the corresponding boundary:

| Area | Evidence-backed guidance | Repository application |
| --- | --- | --- |
| FastAPI background work | [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) distinguishes small post-response work from heavy computation. | Keep native training in the existing worker subprocess, not in a request handler or ordinary BackgroundTasks callback. |
| BFF and request lifecycle | [Next.js Backend-for-Frontend](https://nextjs.org/docs/app/guides/backend-for-frontend) recommends authenticated, validated server-side proxy boundaries and warns about long-running handler limits. | Preserve Browser → Next.js BFF → FastAPI; the BFF starts and observes runs but never trains. |
| Accepted asynchronous requests | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) defines 202 Accepted as accepted but not completed. | Return a run reference and let the dashboard observe durable status. Do not hold the request open for training. |
| Process execution | [Python subprocess](https://docs.python.org/3/library/subprocess.html) documents explicit argument lists, shell=False, and timeout behavior. | Preserve the restricted RetrainingProcessRunner; do not accept command, path, or flag input from the browser. |
| Query polling | [TanStack Query polling](https://tanstack.com/query/v5/docs/framework/react/guides/polling) supports state-dependent intervals that stop when work completes. | Preserve the current active-run polling; consider background-tab polling only if the product explicitly requires it. |
| ML reproducibility | [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness) warns that identical results are not guaranteed across platforms and releases. | Record environment, seed, configuration, device, and code identity; do not promise universal byte identity. |
| Serialization safety | [PyTorch torch.load](https://docs.pytorch.org/docs/stable/generated/torch.load.html), [PyTorch serialization](https://docs.pytorch.org/docs/main/notes/serialization.html), and [Hugging Face model guidance](https://huggingface.co/docs/transformers/models) support restricted loading and safer weight formats. | Preserve weights_only=True, strict reload, trusted revisions, and existing safe packaging. |
| Container mounts | [Docker Compose services](https://docs.docker.com/reference/compose-file/services/) describes service configuration and mounts; [Docker GPU support](https://docs.docker.com/compose/how-tos/gpu-support/) describes explicit device reservations. | Dataset inputs stay read-only; run artifacts and staging stay writable; GPU configuration is an explicit laptop deployment concern, not a browser option. |
| Accessibility status | [WCAG 2.2 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [ARIA25](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA25), and [MDN status](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/status_role) distinguish status updates from focus-changing alerts. | Use a live status region for run-stage changes and reserve alert semantics for actionable failures; do not move focus on every poll. |
| Determinate progress | [MDN progressbar](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/progressbar_role) defines the range/value contract for a real progress bar. | Do not display a percentage unless the backend owns a meaningful numerator, denominator, and restart-safe update. |
| Focus and target size | [WCAG Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible) and [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) provide the relevant interaction requirements. | Preserve visible keyboard focus, usable action targets, and a logical focus order in the existing dark dashboard. |
| Model and dataset reporting | [Model Cards for Model Reporting](https://research.google/pubs/model-cards-for-model-reporting/) and [Datasheets for Datasets](https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/) support documenting intended use, limitations, data provenance, and evaluation context. | Show or link safe dataset/version, preprocessing, device, and evaluation identity; never expose raw requests or secrets. |
| Reproducible experiments | [Reproducibility in Machine Learning for Health](https://www.jmlr.org/papers/v22/20-303.html) identifies data, code, configuration, and environment as reproducibility evidence. | Preserve the existing run manifest and artifact provenance rather than adding a second registry. |
| AI risk management | [NIST AI RMF](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) and its [Playbook](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) emphasize documented evaluation, monitoring, and human oversight. | Training creates a candidate and evidence; it does not activate the candidate or decide deployment. |

### Community evidence use

Recent FastAPI discussions and practitioner reports are useful for discovering operational edge cases around process supervision, timeouts, and restart behavior, but they are not authority for this repository's architecture. Use them to formulate a test or question, then resolve the question against the live worker code, official framework documentation, and an observable local failure boundary. Do not add a queue, scheduler, or external job service because a community post describes a larger deployment.

---

## 6. Architecture boundaries to preserve

The desired control flow is:

~~~
Browser
  -> Next.js route handler / BFF
  -> FastAPI control-plane endpoint
  -> durable local run record
  -> existing worker process boundary
  -> controlled native training adapter
  -> evaluation and provenance artifacts
  -> dashboard polling
~~~

### Browser and BFF

The browser may request a retraining run, read safe run state, and display evidence. It must continue to call only same-origin Next.js routes.

The Next.js BFF must:

- validate request and response payloads with the existing Zod contracts;
- propagate the authenticated actor through the established internal request mechanism;
- call FastAPI with the matching internal API key;
- return safe operational metadata only;
- preserve the existing 202/run-reference behavior for asynchronous work.

The browser must not be able to choose:

- a filesystem path;
- a Python module or shell command;
- a checkpoint or model path;
- a dataset directory;
- a preprocessing version outside the server-controlled profile;
- arbitrary seeds, flags, device strings, or training limits;
- a deployment target or production registry path.

A new request field is justified only if it represents a server-allowlisted product choice. A request field that forwards command-line arguments is a boundary failure.

### FastAPI control plane

FastAPI route handlers remain thin. They authenticate the request, validate the typed input, resolve the actor, call the existing retraining application service, and serialize a safe response.

FastAPI must not:

- perform the long-running training loop;
- open arbitrary paths from request data;
- construct a shell command from request data;
- calculate candidate approval policy in the route;
- mark a candidate active merely because training completed;
- expose raw worker output, request payloads, or secrets.

The existing asynchronous run lifecycle is the source of truth for state. A request returning successfully means the run was accepted, not that a model was trained or approved.

### Durable worker boundary

The worker/coordinator remains responsible for:

- claiming one run;
- acquiring the existing local lock;
- starting and updating heartbeats;
- applying timeout and retry rules;
- invoking the restricted process runner;
- writing stage artifacts and safe events;
- recording bounded failure states;
- releasing the lock and preserving idempotent run state.

The native adapter is a worker child operation, not a new web request path. Keep process arguments explicit and allowlist them, keep shell=False, and retain process-tree termination on timeout.

### Native training adapter boundary

The adapter owns the translation from one validated run/profile into the repository's existing native training and evaluation entrypoints. It should:

1. resolve the run's immutable dataset snapshot and preprocessing contract;
2. construct one server-controlled training configuration;
3. invoke the canonical native training entrypoint;
4. write safe progress and training artifacts under the run;
5. invoke the existing evaluation/evidence path;
6. invoke the existing packaging/provenance path;
7. publish a candidate only after complete evidence is present.

It should not create a new training framework, model registry, scheduler, queue, or policy engine. Reuse the current exporter, snapshot, evaluator, comparator, artifact finalizer, and staging contracts. If an existing entrypoint cannot satisfy the adapter contract, document the exact mismatch and fix that owning boundary rather than duplicating the training algorithm.

### Filesystem and artifact boundary

A successful run should have a truthful, inspectable progression such as:

~~~
run.json
events.jsonl
stages/export.json
stages/dataset.json
stages/training.json
stages/evaluation.json
stages/comparison.json
candidate/...
candidate/serving_manifest.json
candidate/summary_metrics.json
~~~

The exact names must follow the live implementation. The invariant is more important than the names:

- a stage is written only after its inputs and outputs are valid;
- the final manifest is not published before the supporting artifacts exist;
- provenance binds the same dataset, preprocessing, active-model, evaluation-split, training-profile, and source-summary identity;
- a failed or timed-out run cannot look like a complete candidate;
- the active model remains unchanged until explicit administrator-approved staging/deployment.

### Frontend ownership

The UI owns presentation and interaction:

- loading, empty, error, retry, and terminal states;
- polling and stale-refresh behavior;
- stage/heartbeat display;
- evidence tables and safe metadata;
- keyboard/focus behavior;
- responsive layout and readable overflow.

The UI does not own:

- evidence gates;
- ground-truth metric definitions;
- approval policy;
- provenance binding;
- deployment authorization;
- decisions about whether a result is a valid candidate.

---

## 7. Required contracts before native training

### Dataset and preprocessing identity

Native dashboard retraining uses the authoritative v2 pairing: `v3_907k_cleaned_model_input_v2` with `model-input-v2-redacted`. The smoke path binds to the legacy `v3_907k_cleaned` identity without training. The legacy dataset is not silently mixed into native dashboard retraining.

Trace the pairing through:

- the mode-specific source dataset constants, including `RETRAINING_NATIVE_SOURCE_DATASET_VERSION`;
- frozen dataset manifests;
- snapshot manifests;
- preprocessing metadata;
- training configuration;
- the canonical training entrypoint;
- model metadata and loading configuration;
- existing compatibility tests.

Choose the existing authoritative pairing. If a field is missing, fail closed for ambiguous real artifacts rather than silently changing the preprocessing version. Do not regenerate or modify either frozen processed dataset during a dashboard run.

### Approved samples and evaluation split

Approved verified reviews are training inputs. They must not replace the frozen holdout/evaluation split.

The run must preserve one identity for:

- the approved-sample export;
- the cumulative dataset snapshot;
- the frozen evaluation split;
- the evaluation artifact;
- the comparison artifact;
- the final candidate summary;
- the dashboard evidence.

The dashboard proxy based on triage state must not be presented as true ground-truth false-positive rate. Metrics require verified_label ground truth and adequate support; insufficient evidence remains NOT_RUN or an equivalent fail-closed state.

### Fixed server-controlled training profile

For the first laptop-native vertical slice, define one bounded profile in server-side configuration. It should specify, as applicable:

- dataset and preprocessing versions;
- model architecture and trusted base-model identity;
- seed or seed list;
- CPU/GPU device policy;
- precision;
- batch and evaluation batch sizes;
- epoch and sample limits;
- timeout and retry policy;
- output root;
- evaluation and packaging behavior.

The user-facing request should select only “start retraining.” If a profile selector is eventually needed, expose an allowlisted enum that maps to a server-owned configuration. Never pass arbitrary flags through the browser.

---

## 8. Implementation slices

Each slice must leave the repository buildable and must be reviewed before the next slice begins. The agent should record the exact commit, focused checks, broader checks, and any evidence that remains NOT_RUN.

### Slice 0 — Inspect and freeze the baseline

**Purpose:** Establish the actual ownership boundary before editing runtime code.

**Primary files to inspect:**

- ml_model/retraining/dashboard_pipeline.py
- ml_model/retraining/dashboard_worker.py
- ml_model/retraining/run_artifacts.py
- web_app/presentation/dependencies/retraining.py
- web_app/infrastructure/retraining_process_runner.py
- ml_model/training/train.py
- relevant unit/integration tests
- docker-compose.yml, Dockerfile, and any laptop override
- docs/project-ops/ML_MODEL_OPERATIONS_RUNBOOK.md
- docs/project-ops/LAPTOP_TRAINING_HANDOFF.md

**Checklist:**

- [ ] Confirm the current worker defaults to smoke mode and that native mode is selected only by the server-side configuration.
- [ ] Trace the canonical native training and evaluation entrypoints.
- [ ] Confirm the dataset/preprocessing pairing and frozen evaluation source.
- [ ] Confirm which runtime actually executes the worker and where datasets/artifacts are mounted.
- [ ] Identify the smallest existing seam for a server-controlled native profile.
- [ ] Record any uncertain library or platform behavior and research it before implementation.
- [ ] Run the relevant baseline tests before changing behavior.
- [ ] Review git status, git diff, and git diff --check.

**Expected result:** The agent can name the exact function that will launch native training, the exact runtime that will execute it, the exact dataset/preprocessing identity, and the exact artifact directory that will be published.

**Suggested documentation checkpoint:**

~~~
docs(ml): define native laptop training boundary
~~~

### Slice 1 — Implement the native adapter at the worker boundary

**Primary owner:** ml_model/retraining/dashboard_pipeline.py and focused worker/pipeline tests.

Add the smallest implementation that makes NativeDashboardPipeline.execute() perform a bounded native run. Reuse existing export, snapshot, training, evaluation, comparison, packaging, and provenance helpers.

**Required behavior:**

- [ ] A valid native run invokes the canonical native training entrypoint.
- [ ] The adapter receives a validated server-side profile, not raw browser arguments.
- [ ] It writes safe training-stage metadata and heartbeats without logging secrets or raw payloads.
- [ ] It produces an evaluation artifact bound to the intended split and active-model snapshot.
- [ ] It produces a candidate only after complete evidence and provenance validation.
- [ ] It leaves the active model unchanged.
- [ ] A missing dependency, missing dataset, invalid metadata, timeout, nonzero training exit, or incomplete evidence produces a truthful bounded failure.
- [ ] Existing smoke mode remains honest and remains available for CI or environments without training dependencies.

Add focused tests for the success path, one representative missing-runtime failure, and the evidence gate. Do not make a test double the only proof of the public worker path.

**Expected result:** A worker-owned native run can create a candidate or an explicit failure, and neither result is confused with approval or deployment.

**Suggested commit:**

~~~
feat(ml): connect controlled native dashboard training
~~~

### Slice 2 — Make the laptop runtime reproducible

**Primary owner:** Dockerfile/Compose or the existing laptop-specific runtime mechanism.

**Inspect:**

- Dockerfile and Compose service definitions;
- any laptop Compose override, if present;
- requirements.train.txt
- ml_model/configs/training/
- docs/SETUP.md
- docs/project-ops/LAPTOP_TRAINING_HANDOFF.md
- docs/project-ops/ML_MODEL_OPERATIONS_RUNBOOK.md

**Steps:**

- [ ] Prove which training imports fail or are absent inside the actual worker runtime.
- [ ] Add only the existing training dependency file or an existing local override mechanism; do not add a new dependency without approval.
- [ ] Keep dataset mounts read-only and run/artifact mounts writable.
- [ ] Keep secrets in ignored environment files.
- [ ] Keep runtime image behavior unchanged for non-laptop deployments unless the source proves a shared change is necessary.
- [ ] For a Compose-native run, set `INSTALL_TRAINING_REQUIREMENTS=true` and rebuild the backend image before setting `RETRAINING_WORKER_MODE=native`.
- [ ] Define one server-side bounded profile for the first native dashboard run.
- [ ] Ensure the worker cannot receive arbitrary profile values from the browser.
- [ ] Verify the fixed profile's dataset, preprocessing, model architecture, seed, device, precision, sample limits, and output root.
- [ ] Add a focused container/import validation or update an existing runtime test if one owns this boundary.
- [ ] Run docker compose config with the actual laptop override.
- [ ] Build the relevant image and verify the canonical training entrypoint import inside the container.
- [ ] Do not claim native success until the actual worker runtime, not only the host virtual environment, can run the entrypoint.

**Expected result:** The laptop worker has a reproducible training runtime and a server-controlled profile without changing the public request contract.

**Suggested commit:**

~~~
build(ml): provide laptop native training runtime
~~~

If the runtime is already sufficient, leave Docker unchanged and document the verified fact instead.

---
### Slice 3 — Select native mode without weakening the control plane

**Primary owner:** worker wiring, retraining dependency configuration, and API/BFF contract tests.

The laptop environment may select the native adapter through a server-side configuration value or laptop-only Compose override. The browser must not select smoke, native, a command, or a path.

**Checklist:**

- [ ] Keep the public start request stable unless a real contract change is required.
- [ ] Map the laptop environment to the native adapter in one place.
- [ ] Preserve smoke mode for CI and non-training environments.
- [ ] Confirm FastAPI still returns an accepted run reference quickly.
- [ ] Confirm BFF actor propagation and internal API authentication remain unchanged.
- [ ] Confirm retries, timeout, lock loss, and restart reconciliation still apply to native execution.
- [ ] Add or update only tests that prove the public request reaches the correct server-controlled mode.
- [ ] Verify a browser request cannot override the selected profile.

**Expected result:** Clicking Request retraining on the laptop starts a native worker run while the control plane remains a thin asynchronous coordinator.

### Slice 4 — Make the dashboard truthful and useful during native work

**Primary owner:** existing ML Model Operations frontend components, contracts, and tests.

Use the existing run and evidence contracts. Add only the display fields needed to make native progress understandable.

**Checklist:**

- [ ] Show QUEUED, RUNNING, FAILED, PENDING_APPROVAL, SKIPPED, and other existing states distinctly.
- [ ] Show current stage and last heartbeat when available.
- [ ] Show native laptop worker or the safe server-owned runtime identity when that helps the operator.
- [ ] Show dataset snapshot, preprocessing identity, evaluation identity, candidate identity, and evidence state only from backend data.
- [ ] Keep empty approved-data state distinct from a failed worker.
- [ ] Keep PENDING_APPROVAL distinct from deployed or active.
- [ ] Keep retry actionable without losing the durable run record.
- [ ] Use role=status or an equivalent live region for non-disruptive updates; use role=alert only for actionable failures.
- [ ] Preserve keyboard focus and visible focus styling.
- [ ] Test narrow desktop/laptop widths and horizontal overflow for dense evidence tables.
- [ ] Do not add a fake percentage or ETA.

**Expected result:** An operator can tell whether training is queued, running, failed, awaiting review, or merely simulated, without reading logs.

### Slice 5 — Prove the end-to-end laptop path

**Primary owner:** integration tests, runbook, and controlled local demonstration.

Run the smallest proof in layers:

1. static contract and focused unit tests;
2. worker subprocess test with the native profile;
3. container import and runtime test;
4. local dashboard request through BFF and FastAPI;
5. approval, export, and snapshot checks;
6. native training run with bounded laptop limits;
7. evaluation and candidate artifact verification;
8. dashboard candidate review;
9. hold or reject proof that the active model is unchanged;
10. explicit staging/deployment proof only if separately requested and separately gated.

Record:

- exact code commit;
- exact dataset and preprocessing identity;
- exact run ID;
- exact profile and device;
- start and end time;
- stage transitions and heartbeat evidence;
- candidate and evaluation artifact digests;
- final run state;
- whether any model activation occurred.

Do not label a smoke run as native, a candidate as active, or a local proof as hosted or production readiness.

**Expected result:** One controlled click starts a real, bounded laptop training run, the dashboard tracks it from the durable run state, the candidate is reviewable, and the active model remains unchanged until explicit approval and deployment.

**Suggested commit:**

~~~
test(ml): prove dashboard-triggered laptop training
~~~

---

## 9. Frontend standards for this specific UI

### Status and progress

Use existing stage/heartbeat data as the primary progress signal. A stage indicator is truthful even when the training duration is unknown.

Good:

~~~
Training
Native laptop worker
Last heartbeat: 12 seconds ago
Evaluation evidence: not available yet
~~~

Bad:

~~~
Training 63%
~~~

unless the backend can prove what the percentage measures and can update it consistently after restart.

When a determinate progress value is eventually introduced:

- define its units and denominator in the backend contract;
- expose valid aria-valuenow, aria-valuemin, and aria-valuemax values;
- keep a textual equivalent;
- omit determinate values when progress is unknown;
- test updates without focus movement.

### Error and empty states

Keep these distinct:

- loading;
- successful empty state;
- failed request with retry;
- active run with incomplete evidence;
- failed run with safe next action;
- recovery-required deployment state.

Do not render a missing evaluation result as a zero score or a failed backend request as “no data.”

### Responsive behavior

The current Model Operations CSS already uses responsive grids and horizontal scrolling for dense run data. Preserve that strategy unless live testing demonstrates a concrete failure.

Validate:

- 320px and 375px narrow widths;
- a medium laptop width;
- a wide desktop width;
- keyboard-only navigation;
- browser zoom where practical;
- horizontal table access without clipped controls;
- stable headings and status messages when content changes.

Do not replace the dense table with cards merely because a card layout is fashionable. The table contains repeated exact mappings—run ID, dataset, candidate, status, attempt, heartbeat, and creation time—where horizontal scrolling can be more truthful than hiding columns.

### State management

Use the existing TanStack Query keys and invalidation rules. Do not add global state for a selected run or training profile unless a real cross-page requirement exists.

Polling should stop for terminal states. Background-tab polling is a product choice, not an automatic correctness fix.

---

## 10. Test strategy

Tests should establish meaningful contracts, not inflate coverage.

### Backend unit boundaries

Start with the smallest relevant test:

~~~
.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_retraining_worker.py
~~~

Then run the native pipeline and artifact-contract tests that actually own the changed behavior:

~~~
.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_retraining_worker.py tests/unit/test_retraining_run_artifacts.py tests/unit/test_dashboard_contracts.py tests/unit/test_dashboard_export.py tests/unit/test_dashboard_dataset.py tests/unit/test_retraining_evidence.py tests/unit/test_native_distilbert_artifact_flow.py
~~~

Add a new focused test file only when no existing owner is appropriate. Do not add a broad generic mock-worker framework.

### Required behavioral tests

At minimum, prove:

- smoke mode remains honest and does not claim native quality;
- native mode executes the canonical entrypoint;
- successful native mode publishes stages in order;
- native failure and timeout are bounded and recoverable;
- training dependencies are available in the actual worker runtime;
- the dataset mount is read-only and artifact output is writable;
- dataset/preprocessing metadata remains compatible;
- source snapshot is captured once and cannot produce mixed provenance;
- ordinary summary metric mutation is detected;
- required metrics reject booleans, strings, nulls, objects, and lists where numeric values are required;
- evaluation uses verified labels and the correct split;
- a candidate cannot reach approval without complete evidence;
- hold/reject leaves the active model unchanged;
- a second request cannot create a duplicate run for the same fingerprint;
- restart/timeout behavior leaves a truthful durable state.

### API/BFF tests

Run the existing direct contract tests before adding new ones:

~~~
.venv\Scripts\python.exe -m pytest -q --tb=short tests/integration/test_retraining_api.py
~~~

~~~
cd frontend
npx vitest run --pool=threads app/api/ml-model-routes.test.ts
~~~

The BFF tests must continue to prove:

- browser requests cannot choose paths or flags;
- actor identity and role are propagated;
- viewers can read but cannot decide/deploy;
- typed validation occurs before the backend call;
- safe errors do not expose secrets or raw payloads.

### Frontend tests

Run the existing Model Operations tests:

~~~
cd frontend
npx vitest run --pool=threads components/ml-model/MLModelWorkspace.test.tsx
npm run lint
npm run typecheck
~~~

Add frontend tests only for behavior such as:

- native versus smoke labeling;
- active stage/heartbeat rendering;
- error versus empty state distinction;
- accessible status announcements;
- keyboard action behavior;
- responsive control visibility when a real regression is demonstrated.

Do not test CSS class strings when a rendered semantic behavior can be tested instead.

### Local container and dashboard proof

Use the actual laptop runtime, not only the host virtual environment:

~~~
docker compose config
docker compose build backend frontend
docker compose ps
docker compose exec backend python -c "import torch, transformers; print(torch.__version__); print(transformers.__version__)"
~~~

Then perform the dashboard run and record:

- initial active model identity;
- approved-sample count;
- run ID;
- observed states and timestamps;
- dataset snapshot identity;
- candidate/evaluation/summary digests;
- final run state;
- active model identity after training;
- whether deployment was intentionally not run.

If the native run is not executed, report NOT_RUN. Do not call the smoke run native proof.

---

## 11. Failure handling and iteration loop

After every meaningful change:

1. Run the smallest relevant test or reproduction.
2. Read the complete failure output.
3. Identify the owning boundary.
4. Fix the root cause at that boundary.
5. Rerun the focused check.
6. Run adjacent owner-level tests.
7. Inspect the diff for duplicated logic, hidden races, stale assumptions, and unrelated changes.

Do not respond to a failing test by:

- weakening a valid assertion;
- adding a conditional only for the test fixture;
- adding a second implementation of the same policy;
- swallowing the exception;
- expanding the retry budget without understanding the failure;
- creating a generic framework for one fault scenario.

### Common failure interpretations

| Symptom | Investigate first | Do not do first |
| --- | --- | --- |
| Native import failure | Actual worker image/interpreter and installed requirements | Add arbitrary dependencies to the base image |
| Run reaches training but no artifacts appear | Native adapter ownership and run-local output path | Add UI polling or sleep loops |
| Candidate has missing metrics | Evaluation/provenance finalizer and required evidence contract | Display zeros or bypass the gate |
| Dashboard shows stale state | BFF response, query key, invalidation, and worker heartbeat | Add faster polling blindly |
| Training process hangs | subprocess timeout, heartbeat, child process ownership, and logs | Add an unbounded timeout |
| Different dataset/preprocessing metadata | Run contract and authoritative version source | Silently rewrite metadata |
| UI screen-reader noise | Live-region role, update frequency, and focus behavior | Add role=alert everywhere |
| Narrow layout clips a table | Table's local overflow and actual viewport behavior | Hide columns without a product decision |

---

## 12. Risks and trade-offs

### Backend runtime versus separate training service

Running the native adapter through the existing isolated worker is the smallest compatible change. A separate training service may improve dependency isolation, but it introduces another process/service contract and is not justified until the current runtime is proven insufficient.

### CPU versus GPU

CPU is the portable first validation path. GPU support is an operator/runtime concern and depends on the laptop, Docker engine, driver, and PyTorch build. Do not let a browser request select a device. A failed GPU setup should be reported as BLOCKED or use the approved CPU profile, not silently change the evidence label.

### Polling versus streaming

Polling is simpler, restart-friendly, and already implemented. SSE/WebSockets would add connection lifecycle and proxy complexity. Do not introduce streaming unless measured requirements show that three-second active polling is inadequate.

### Native progress versus truthful stage state

Stage and heartbeat are reliable even when duration is unknown. A numeric progress bar is more attractive but becomes misleading if the training loop, evaluation, or restart semantics cannot support it. Prefer truthful stage state first.

### Manual exported-data training

Manual training is acceptable for early laptop validation, but it is not the final dashboard contract. It can prove that the canonical training entrypoint works; it cannot prove that the dashboard has preserved run identity, snapshot binding, evidence, and approval semantics.

### Model-quality claims

A successful bounded smoke run proves runtime execution and failure handling. It does not prove that the candidate is better, safe for production traffic, or suitable for thesis-quality claims. Full quality claims require the established baseline, evaluation, support, confidence/uncertainty evidence, and project-approved gates.

---

## 13. Intentionally deferred

Do not implement these as part of the native laptop slice:

- Redis, Celery, Kafka, Airflow, Temporal, Kubernetes, MLflow, or a hosted workflow engine.
- A distributed lock or external lease service.
- A new database schema or hosted run-history system.
- A new model registry or signing/PKI system.
- Automatic production promotion or production rollback.
- Browser-selectable training commands, paths, flags, or arbitrary profiles.
- A broad frontend state-management rewrite.
- SSE/WebSockets or a generic progress framework.
- New macro-F1, FPR, source-diversity, or deployment policy.
- Replacing the frozen processed dataset or evaluation holdout.
- Treating false_positive as a training class.
- Rewriting the existing BFF or authentication architecture.
- Reformatting unrelated dashboard components.

Reconsider a deferred item only when a concrete repository-scoped failure demonstrates that the current architecture cannot satisfy the actual laptop requirement.

---

## 14. Final review checklist

### Contract and architecture

- [ ] Browser → Next.js BFF → FastAPI remains intact.
- [ ] FastAPI remains a thin control plane.
- [ ] Training is outside the request lifecycle.
- [ ] The worker remains the owner of claim/lock/heartbeat/timeout/retry behavior.
- [ ] Native training is owned by one clear pipeline adapter.
- [ ] No duplicate training loop or policy engine was introduced.

### Data and evidence

- [ ] Approved verified reviews are the only new training inputs.
- [ ] The snapshot is cumulative and reusable.
- [ ] The frozen holdout/evaluation split is preserved.
- [ ] Dataset and preprocessing versions agree everywhere.
- [ ] Source summaries are not reopened later to create mixed provenance.
- [ ] Required numeric metrics are validated as numeric JSON values, excluding booleans.
- [ ] Summary content integrity is verified.
- [ ] Candidate, evaluation, active-model, and decision bindings are intact.

### Runtime and security

- [ ] The actual worker runtime contains the required training dependencies.
- [ ] Dataset mount is read-only.
- [ ] Run artifacts are writable only where intended.
- [ ] Subprocess invocation uses an explicit argument list and shell=False.
- [ ] Browser input cannot select paths, commands, flags, or secrets.
- [ ] Raw payloads, credentials, and unbounded worker output are not exposed.
- [ ] Timeout, lock loss, process death, and restart behavior are tested or explicitly marked NOT_RUN.

### Frontend and accessibility

- [ ] Native, smoke, failed, incomplete, and pending-approval states are visibly distinct.
- [ ] The UI does not invent metrics or progress.
- [ ] Status updates are polite and programmatically available.
- [ ] Errors use alert semantics only when urgent.
- [ ] Focus does not move during polling.
- [ ] Keyboard navigation and visible focus work.
- [ ] Dense data remains accessible at narrow widths.
- [ ] No direct browser-to-FastAPI request exists.

### Validation and review

- [ ] Focused failing tests were written for new behavior where practical.
- [ ] Focused tests were run before broader suites.
- [ ] Backend affected suites pass or have documented failures.
- [ ] Frontend tests, lint, and typecheck pass when frontend code changed.
- [ ] Container/runtime validation was performed when runtime files changed.
- [ ] Local dashboard behavior was manually verified when the environment permitted it.
- [ ] git diff --check passes.
- [ ] git status --short is understood.
- [ ] No generated artifacts, secrets, or unrelated changes are staged.
- [ ] Every claim is labeled PASS, FAIL, NOT_RUN, BLOCKED, or UNRELATED_FAILURE accurately.

### Stop condition

Stop when the completion gate is satisfied, the relevant evidence is recorded, and the remaining work is explicitly deferred or blocked. Do not continue refactoring merely because another abstraction could be imagined.

The implementation is not ready if the dashboard still reaches only the smoke worker, if native evidence is missing, if provenance is not bound end to end, or if the active model can change without explicit approval and deployment.

---

## 15. Implementation record

The implementation agent should append a concise record here as work progresses rather than creating a second status document:

~~~
Slice:
Commit:
Files changed:
Research decision(s):
Focused validation:
Adjacent validation:
Manual/local proof:
Known limitations:
Next slice:
~~~

Keep this record factual. Do not write “complete” until the native dashboard-triggered path has actually been exercised or the exact remaining blocker is documented.
