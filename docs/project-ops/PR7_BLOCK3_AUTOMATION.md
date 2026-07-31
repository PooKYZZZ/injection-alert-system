# PR7 Block 3 proof automation

The repository now provides bounded operator scripts for repeatable Section 3B
and 3C evidence collection. They package only allowlisted metadata; credentials,
cookies, request values, prompts, and response bodies are never written.

## Local preflight

From the repository root:

```powershell
python -m scripts.pr7_block3_preflight --profile 3b --run-id run-20260731 --output artifacts/pr7-block3/run-20260731/preflight-3b.json
python -m scripts.pr7_block3_preflight --profile 3c --run-id run-20260731 --output artifacts/pr7-block3/run-20260731/preflight-3c.json
```

The preflight checks the required Compose files, Docker client/daemon, and (for
3B) only the presence of the Cloudflare token file. It never reads the token.

## Disposable stack lifecycle

The stack wrapper uses a run-specific Compose project name and always removes
volumes and orphan containers on stop:

```powershell
python -m scripts.pr7_block3_stack start --profile 3c --run-id run-20260731
python -m scripts.pr7_block3_stack stop --profile 3c --run-id run-20260731
```

Use the 3B profile only when the local token and test-only environment variables
are already configured. Hosted and production enforcement are never enabled by
these commands.

## External source agent and coordinator

Live probing is deliberately opt-in and requires `PR7_RUN_BLOCK3_LIVE=1`.
Run the source agent once from each genuinely distinct network (for example,
home broadband and mobile data), using the same `run-id`:

```powershell
$env:PR7_RUN_BLOCK3_LIVE = "1"
python -m scripts.pr7_block3b_source_agent --proof-url https://target-proof.example/records/search --run-id run-20260731 --source-label home --output artifacts/pr7-block3/run-20260731/home.json
```

The second source must be a real independent egress; a VPN exit is not treated
as proof of source equivalence unless the network boundary is independently
validated. Then correlate the two bundles:

```powershell
python -m scripts.pr7_block3b_coordinator --run-id run-20260731 --source artifacts/pr7-block3/run-20260731/home.json --source artifacts/pr7-block3/run-20260731/mobile.json --output artifacts/pr7-block3/run-20260731/coordinator.json
```

The coordinator reports `PASS` only for the source-level normal, static CRS,
and forged-header assertions. WAF transaction, bridge, model, revision, and
portal sentinel records must be supplied by the local harness or operator
artifacts; the coordinator does not fabricate those correlations.

## 3C runner and finalization

```powershell
python -m scripts.pr7_block3c_runner --run-id run-20260731 --output artifacts/pr7-block3/run-20260731/3c-focused.json
python -m scripts.pr7_block3c_runner --run-id run-20260731 --disposable --output artifacts/pr7-block3/run-20260731/3c-disposable.json
python -m scripts.pr7_block3_finalize --preflight artifacts/pr7-block3/run-20260731/preflight-3b.json --coordinator artifacts/pr7-block3/run-20260731/coordinator.json --output artifacts/pr7-block3/run-20260731/final.json
```

For a real-model disposable startup on slower hosts, the lifecycle harness
accepts `PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS` from 60 through 900 seconds. The
default remains 180 seconds; a short-TTL run can use, for example,
`PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS=600` and
`PR7_BLOCK3_RECOMMENDATION_TTL_SECONDS=60`.

The focused runner executes the existing deterministic 3C harness and capacity
tests. Disposable mode executes the existing Compose-backed lifecycle suite and
records only a bounded output tail. Cleanup remains owned by that existing
harness and must be verified with `docker ps`, `docker network ls`, and
`docker volume ls` after the run.

`final.json` always contains `hosted_or_production_ready: false`. A successful
local report is not a hosted rollout authorization and does not replace the
required two-network Cloudflare proof.
