# ML Model Operations Runbook

**Status:** implemented for controlled local operation; hosted and production
promotion are not implemented or verified.

This runbook describes the local Model Operations workspace and its explicit
review boundary. It is an operational guide, not evidence that a hosted model
deployment exists.

## Safety boundary

The request path is:

```text
Browser -> Next.js BFF -> FastAPI control plane -> durable local run artifacts
                                                    -> worker -> candidate evidence
                                                    -> explicit Owner staging action
```

Browser code cannot select filesystem paths, shell commands, model paths, or
training flags. The worker and scheduled wrapper can create or start a run,
but neither can approve, deploy, or rollback a model. The local staging adapter
never writes `ml_model/model_registry/production/`.

The default controlled-local settings are:

```text
RETRAINING_OUTPUT_ROOT=ml_model/results/dashboard_retraining
RETRAINING_STAGING_ROOT=ml_model/model_registry/staging
RETRAINING_STAGING_ARCHIVE_ROOT=ml_model/model_registry/archive
RETRAINING_SCHEDULE_TIMEZONE=Asia/Manila
```

These are server-side settings. They are not request fields and must remain in
ignored environment/configuration files where overridden.

### Container persistence

When the backend runs through the repository Compose files, the three
controlled-local runtime roots are bind-mounted from the checkout:

```text
ml_model/results/dashboard_retraining -> /app/ml_model/results/dashboard_retraining
ml_model/model_registry/staging      -> /app/ml_model/model_registry/staging
ml_model/model_registry/archive      -> /app/ml_model/model_registry/archive
```

Create the results directory if it does not exist before the first Compose
start. These paths preserve run manifests, events, evidence, and controlled
staging/archive state across backend image rebuilds and container recreation.
They remain local runtime state; the production registry is not mounted and
the web app never writes to it.

## Reviewer workflow

1. An Owner starts a manual run, or the scheduled wrapper requests one.
2. The server resolves the latest eligible approved reviews and binds the run
   to dataset, active-model, preprocessing, and pipeline identities.
3. Export, cumulative snapshot creation, training, and evaluation write
   manifest-tracked artifacts under the run directory.
4. The run enters `pending_approval` only after the worker records its result.
   A reviewer checks the dataset/version, candidate identity, evaluation
   evidence, active-model binding, and comparison gates.
5. An Owner chooses approve, hold, or reject. Hold and reject leave
   the active model unchanged. Approved is only a decision state; it does not
   activate the candidate.
6. The Owner explicitly selects Deploy from ML Deployment. The
   server rechecks the run state, evidence hashes, gate result, active binding,
   serving manifest, allowlisted files, preprocessing version, label map, and
   CPU load/prediction smoke before copying to local staging.
7. A successful deployment records the prior staging version and archive
   identity, validates a private candidate copy, and keeps the previous
   staging directory in place until the active pointer names the candidate.
   It then archives the predecessor, reloads the model, and records `deployed`.
   A load failure restores and verifies the previous model and records
   `rolled_back`.
8. Rollback is a separate Owner action bound to the deployment record
   and the requested previous staging version. If the process exits while the
   run is `deploying`, the same action reconciles a still-active predecessor
   back to `approved`, or completes a physically finished rollback to
   `rolled_back`; an ambiguous pointer or digest remains `RECOVERY_REQUIRED`.

## States and evidence

Run state is durable in `run.json`; audit events are append-only in
`events.jsonl`. Important operation codes include:

| Operation | Required result |
| --- | --- |
| scheduled request with no approved input | `SKIPPED_NO_APPROVED_DATA` |
| scheduled request during another active run | `SCHEDULE_SKIPPED_CONCURRENT_RUN` |
| candidate review | `APPROVED`, `HELD`, or `REJECTED` |
| deployment start/success | `DEPLOY_STARTED`, `DEPLOY_SUCCEEDED` |
| load failure with known-good restore | `DEPLOY_ROLLED_BACK`, run `rolled_back` |
| rollback start/success | `ROLLBACK_STARTED`, `ROLLBACK_SUCCEEDED` |
| interrupted deployment recovery | `DEPLOYMENT_RECONCILED` or `ROLLBACK_RECONCILED` |

Deployment requires native or verified passing evaluation evidence and a
passing comparison whose provenance matches the run's active and candidate
digests. Proxy metrics, missing evidence, tampered artifacts, stale active
bindings, and aggregate-only improvements cannot produce a deployment pass.

The repository's default comparison tolerances are controlled demonstration
policy values, not universal cybersecurity thresholds: Normal FPR increase and
attack-escape increase are each limited to `0.001`, Normal recall must remain
at least `0.995`, supported attack recall may drop by at most `0.01`, and macro
F1 may drop by at most `0.002`. The comparison contract also requires a
meaningful macro-F1 improvement and passing security-critical gates. The
evaluation artifact and comparison provenance are the source of truth for a
particular run.

## Artifact layout and retention

Each run is a direct child of `RETRAINING_OUTPUT_ROOT`. The repository protects
the run manifest and hashes JSON artifacts in its artifact manifest. Candidate
serving files are copied only from the run's `candidate_model` directory after
allowlist, manifest, digest, and reload validation.

Local staging contains the currently active controlled-local artifact. Previous
artifacts are moved to the configured archive root with a run/time-qualified
name after the active pointer has switched. `staging/deployment.json` binds the
candidate, previous version, hashes, preprocessing version, and operation
status. This ordering keeps either the old or new pointer target present across
an ordinary process interruption.

Preserve run manifests, events, evaluation/comparison evidence, and deployment
records for the capstone review period. Keep the previous staged artifact until
the next known-good replacement is verified. No automated retention or
physical-delete job is implemented; cleanup requires an explicit, reviewed
local operation and must not remove the active or required evidence artifact.

## Daily scheduling

The wrapper makes one bounded request and never performs catch-up loops,
approval, deployment, or rollback:

```powershell
.\scripts\retraining\run_daily_retraining.ps1
```

It expects server-side `API_SECRET_KEY`; the key is sent only as an
Authorization header and is never printed. Override `FASTAPI_BASE_URL` and
`RETRAINING_SCHEDULE_TIMEZONE` in the scheduler environment when needed. The
wrapper prints only the run id, bounded status, stage, creation flag, schedule
and request-completion timestamps, timezone, and exit code.

For Windows Task Scheduler, create a daily task that runs PowerShell with
`-NoProfile -File <absolute-repository-path>\scripts\retraining\run_daily_retraining.ps1`,
using an account allowed to reach the controlled-local FastAPI service. Set a
bounded timeout and capture the small status line as task output. Task
installation is not part of this repository proof and is **NOT_RUN** here.

## Troubleshooting matrix

| Symptom/status | Meaning | Safe action |
| --- | --- | --- |
| `SKIPPED_NO_APPROVED_DATA` | No eligible approved review snapshot | Review labels; do not force a run |
| `SCHEDULE_SKIPPED_CONCURRENT_RUN` | Another queued/active/review run exists | Inspect that run; wait for its decision |
| `NOT_ENOUGH_EVIDENCE` | Required evaluation/support is missing | Do not approve or deploy; complete evaluation |
| `INVALID` evidence | Published evaluation evidence is missing, unreadable, or fails integrity validation | Preserve the run artifacts; do not approve or deploy; investigate the failed artifact boundary |
| `DEPLOY_GATE_FAILED` | Comparison policy failed | Inspect per-gate evidence; hold/reject |
| `DEPLOYMENT_RECOVERY_REQUIRED` | Pointer/digest state is ambiguous after an interrupted deployment | Stop automated actions; inspect the run plan and staging/archive digests manually |
| integrity/metadata failure | Candidate or deployment artifact changed | Preserve the failure evidence and reject the candidate |
| load verification failure | Candidate could not load or smoke-test | Confirm the run is `rolled_back`; keep the prior model |
| `ROLLBACK_RECOVERY_REQUIRED` | Rollback state cannot prove which artifact is active | Do not delete files; inspect the pointer and both artifact digests manually |
| rollback failure | Previous artifact could not be verified | Do not delete files; inspect staging/archive integrity manually |
| scheduler request failure | FastAPI/auth/service unavailable | Check service and server-side configuration; rerun once |

## Evidence boundary

Automated tests and controlled-local checks prove the contracts listed above.
They do not prove native laptop training quality, hosted Cloudflare/production
connectivity, production model activation, or an installed Windows scheduled
task. Those remain separate evidence items and are currently **NOT_RUN** unless
fresh external proof is recorded.
