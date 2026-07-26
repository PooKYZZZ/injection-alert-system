# Codex Token-Efficiency Measurement Protocol

Status: **Planned — benchmark not run**

This note defines a directional comparison between the current baseline and the
lean Codex setup. The lean configuration is accepted by the installed CLI, but
the benchmark has not run and no percentage reduction is claimed. The current
CLI cannot runtime-verify the specialized profiles because it reports that the
configured model requires a newer Codex version.

## Initial paired tasks

Run 10 comparable bounded CyberTrace tasks once in each cohort, for 20 runs total:

1. Documentation edit
2. Backend test fix
3. Frontend test fix
4. BFF change
5. Security review
6. Git inspection
7. Log triage
8. Docker/Compose inspection
9. Playwright/UI check
10. Architecture investigation

Use a fresh task for every run. Keep the requested outcome, repository state,
and acceptance check comparable. Record the model, reasoning effort, profile,
turn count, tool calls, files read more than once, compactions, repeated tests,
and quota movement. A run passes only when the normal acceptance check passes
without hidden failures or human correction.

## Cohorts

- **Baseline:** existing setup before the lean profile is used.
- **Lean:** default Codex configuration after this change.
- **RTK:** future optional cohort only after a trusted installation exists; do
  not install RTK or include it in the initial calculation.

## Current evidence boundary

- Base config: strict validation accepted; `tool_output_token_limit = 8000` is
  accepted configuration, not a measured savings result.
- Specialized profiles: `CONFIG_VALID_RUNTIME_UNVERIFIED` or `BROKEN`; none is
  counted as working.
- Context7: disabled and `NOT_RUN` because no handshake or harmless lookup was
  performed.
- Codebase Memory: `DISABLED_PENDING_SAFE_REPAIR` because its configured
  executable is unavailable.
- Generic plugin enablement: `UNVERIFIED_NO_CHANGE` because the installed CLI
  did not verify a generic plugin state key.

## Result table

| Task | Cohort | Model/effort | Turns | Tool calls | Files reread | Compactions | Repeated work | Quota movement | Acceptance |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1–10 | Baseline / Lean | Not run | — | — | — | — | — | — | NOT_RUN |

## Interpretation rule

Count the lean setup as successful only if it reduces usage or repeated work
without reducing correctness, hiding failure details, increasing retries, or
requiring more human correction. Do not use community percentage claims as
local evidence.
