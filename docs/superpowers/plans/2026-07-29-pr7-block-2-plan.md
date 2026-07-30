# PR7 Block 2 Controlled Local WAF Runtime Implementation Plan

> **For agentic workers:** Implement inline task-by-task with test-first checkpoints.

**Goal:** Build and verify the controlled local PR7 WAF runtime end to end without changing hosted, staging, production, frontend, ML, or Supabase behavior.

**Architecture:** Add a focused synchronous Python runtime package for strict snapshot ingestion, canonical validation, deterministic ModSecurity rendering, persistent candidate state, NGINX activation/probing/rollback, reconciliation, controls, and PID-1 supervision. Derive the local WAF service from the pinned CRS image while preserving its bootstrap and static CRS includes.

**Tech Stack:** Python, httpx, Pydantic, pytest, NGINX, ModSecurity/OWASP CRS, Docker Compose, PowerShell validation.

---

### Task 1: Runtime contracts and strict snapshot client

**Files:**
- Create: `waf_runtime/config.py`, `waf_runtime/snapshot.py`, `waf_runtime/__init__.py`
- Test: `tests/waf_runtime/test_snapshot.py`, `tests/waf_runtime/test_config.py`

- [ ] Write failing tests for fixed-origin URL validation, bearer/JSON headers, no redirects/proxy environment, bounded streaming, content type/encoding, UTF-8/BOM, duplicate keys, strict types, unknown fields, limits, timestamps, IP policy, identities, and checksum compatibility.
- [ ] Run the focused tests and confirm feature-missing failures.
- [ ] Implement the smallest synchronous client/parser/validator using the exact Block 1 checksum algorithm and whole-snapshot atomicity.
- [ ] Run focused tests and confirm green.
- [ ] Commit `feat: add PR7 snapshot client and deterministic renderer` after renderer work below.

### Task 2: Deterministic ModSecurity renderer

**Files:**
- Create: `waf_runtime/render.py`
- Test: `tests/waf_runtime/test_render.py`, `tests/waf_runtime/test_vectors.py`

- [ ] Add failing golden tests for 0/1/64/128/512 entries, permutation invariance, IDs 10000–10511, fixed grammar/tags/message, expiry, checksum, and collision rejection.
- [ ] Implement canonical ordering and safe fixed-syntax rule rendering with final newline and no arbitrary input in rule syntax.
- [ ] Run golden and checksum tests, then add shared vectors against the Block 1 implementation.

### Task 3: Persistent candidate state and atomic file operations

**Files:**
- Create: `waf_runtime/state.py`
- Test: `tests/waf_runtime/test_state.py`

- [ ] Write failing tests for stable lock inode, exclusion, atomic replacement, regular-file/symlink checks, metadata recovery, previous preservation, canonical empty protection, pruning, and volume recreation semantics.
- [ ] Implement `/pr7-state` layout with `fcntl.flock`, temp-file fsync/replace, checksums, protected files, selected metadata, previous candidate, and persistent disabled latch.
- [ ] Run state tests and commit `feat: add PR7 candidate activation and rollback` after NGINX control work below.

### Task 4: NGINX validation, reload, generation, probe, and rollback

**Files:**
- Create: `waf_runtime/nginx.py`, `waf_runtime/activation.py`
- Test: `tests/waf_runtime/test_activation.py`, `tests/waf_runtime/test_nginx.py`

- [ ] Write failing tests for syntax failure, reload failure, unchanged generation, candidate-specific fresh-connection probe failures, static CRS/no-upstream/source/path controls, metadata failure, previous fallback, empty fallback, and unrecoverable rollback.
- [ ] Implement bounded subprocess control, worker-generation observation, fresh-connection probe interface, activation ordering, rollback, and safe diagnostics.
- [ ] Run focused activation tests and confirm selected metadata is committed only after confirmation.

### Task 5: Modes, reconciliation, controls, and structured logs

**Files:**
- Create: `waf_runtime/reconcile.py`, `waf_runtime/logging.py`
- Test: `tests/waf_runtime/test_reconcile.py`, `tests/waf_runtime/test_controls.py`, `tests/waf_runtime/test_logging.py`

- [ ] Write failing tests for OFF/DRY_RUN/ENFORCE, disabled latch, no-change fast path, outages, expiry, recovery de-duplication, lower/equal revisions, serialised enable/disable, shutdown boundaries, and secret/payload redaction.
- [ ] Implement the synchronous loop, explicit controls/status command, bounded retry/degraded state, safe structured events, startup recovery, and final disabled-empty behavior.
- [ ] Run all pure runtime tests and commit `feat: add PR7 runtime controls and supervision` after supervision work below.

### Task 6: PID-1 supervisor and pinned local image

**Files:**
- Create: `waf_runtime/supervisor.py`, `waf_runtime/entrypoint.py`, `Dockerfile.pr7-waf`, `config/modsecurity/pr7-dynamic-include.conf.template`
- Modify: `docker-compose.yml`
- Test: `tests/waf_runtime/test_supervisor.py`, `tests/scripts/test_pr7_compose.py`

- [ ] Write failing process tests for bootstrap preservation, child death, SIGQUIT/SIGTERM/SIGINT, reaping, and bounded shutdown.
- [ ] Implement the minimal PID-1 process supervisor and local-only Compose service/volume wiring without changing the existing technical or hosted profiles.
- [ ] Run process tests and inspect the pinned image architecture, entrypoint, command, user, stop signal, NGINX/ModSecurity/CRS versions, include tree, and writable paths before image build.

### Task 7: Controlled local integration and evidence

**Files:**
- Create/modify: `tests/e2e/test_pr7_local_waf.py`, `scripts/measure_pr7_runtime.py`, `docs/project-ops/PR7_BLOCK_2_EVIDENCE.md`

- [ ] Add controlled tests for eligible blocking, no portal reach, wrong source/path, forged headers, expiry while backend/poller are unavailable, revocation, CRS, and PR6 regressions.
- [ ] Add bounded measurements at 0/1/64/128/512 rules for render, syntax, reload-generation, probe, and rollback timings.
- [ ] Run Docker/Compose recreation, source-correlation, CRS, PR6, process, secret-scan, Ruff, compileall, migration, and relevant backend suites; record exact PASS/FAIL/NOT_RUN results.
- [ ] Leave the local runtime latched disabled and empty and commit `test: validate PR7 local WAF runtime enforcement`.

### Task 8: Review and publication

- [ ] Review `git diff --check`, secrets, generated files, hosted/staging/production diffs, and final state.
- [ ] Commit any documentation corrections.
- [ ] Push `feat/pr7-waf-runtime` and open one draft PR titled `Implement PR7 Block 2 local WAF runtime` if GitHub authentication is available; otherwise report the exact external blocker and leave the branch ready for publication.
