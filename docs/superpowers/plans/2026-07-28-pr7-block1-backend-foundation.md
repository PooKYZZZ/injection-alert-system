# PR7 Block 1 Backend Foundation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification checkpoints. Do not start Block 2.

**Goal:** Implement PR7 T1/T2/T3 as one additive backend foundation with PostgreSQL-enforced lifecycle state, atomic mutation, repeatable-read snapshots, and an authenticated controlled-local API.

**Architecture:** Preserve `enforcement_recommendations` as historical input. Add dedicated effective-state and singleton revision persistence in `web_app/infrastructure/database/database.py` and a single Alembic migration. Add focused domain/application/infrastructure/presentation modules following existing async SQLAlchemy and FastAPI conventions.

**Tech Stack:** Python, FastAPI, Pydantic v2, SQLAlchemy async sessions, Alembic, PostgreSQL/asyncpg, pytest.

---

### Task 1: Prepare branch and baseline evidence

**Files:** Git branch only; no source edits.

- [ ] Switch/create `feat/pr7-critical-waf-enforcement` from the current T0 base.
- [ ] Record current HEAD, migration head, SQLAlchemy/driver versions, recommendation model/transaction boundary, auth/error conventions, and PostgreSQL fixture availability without reading secrets.
- [ ] Confirm worktree is clean and real Supabase is not used.

### Task 2: Add schema and migration tests first

**Files:**
- Create: `tests/migrations/test_pr7_effective_waf_state_migration.py`
- Modify: `web_app/infrastructure/database/database.py`
- Create: `migrations/versions/20260728_000025_add_pr7_effective_waf_state.py`

- [ ] Add failing tests for singleton initialization, exact lifecycle/status constraints, unique recommendation ownership, partial ACTIVE `(source_ip, protected_path)` uniqueness, restricted recommendation deletion, expiry/terminal consistency, and upgrade/downgrade/re-upgrade.
- [ ] Add ORM rows for the singleton control state and effective WAF state without changing historical recommendation lifecycle columns.
- [ ] Implement the additive migration with deterministic revision `0`, bounded fields, named constraints/indexes, and repository security conventions.
- [ ] Run focused migration tests and static migration inspection.

### Task 3: Add canonical domain and wire-contract tests

**Files:**
- Create: `web_app/domain/waf_state.py`
- Create: `web_app/presentation/schemas/waf_enforcement.py`
- Create: `tests/unit/test_pr7_waf_state_contract.py`

- [ ] Test IPv4, IPv6, mapped IPv6, malformed addresses, path bounds, aware datetime formatting, exact lifecycle transitions, canonical item ordering, checksum stability, and logical checksum changes.
- [ ] Implement typed domain values/results and exact Pydantic snapshot/item models with extra-field rejection.
- [ ] Implement explicit UTC formatting and canonical checksum serialization using the normative fields and ordering.

### Task 4: Add mutation repository/application tests first

**Files:**
- Create: `web_app/application/waf_state_use_cases.py`
- Create: `web_app/infrastructure/repositories/waf_state_repository.py`
- Create: `tests/integration/test_pr7_waf_state_postgres.py`

- [ ] Add PostgreSQL tests for first activation, duplicate/no revision, extension, supersession, revocation, terminal non-resurrection, expiry cleanup, capacity finality, lock ordering, lock-wait clock behavior, same-key concurrency, different-key serialization, and injected rollback.
- [ ] Implement transaction-scoped mutation with `READ COMMITTED`, singleton-first lock, PostgreSQL `clock_timestamp()`, atomic recommendation/effective-state changes, one revision per desired-state change, and typed non-activation results/logging.
- [ ] Implement explicit cleanup and revoke paths without physical deletion of traffic/recommendation history.
- [ ] Run focused PostgreSQL tests; classify environment failures rather than weakening contracts.

### Task 5: Add repeatable-read snapshot tests and implementation

**Files:**
- Modify: `web_app/application/waf_state_use_cases.py`
- Modify: `web_app/infrastructure/repositories/waf_state_repository.py`
- Modify: `tests/integration/test_pr7_waf_state_postgres.py`

- [ ] Test `repeatable read` and `read only`, stable revision/entries under concurrent commit, passive expiry stability, and explicit cleanup visibility.
- [ ] Configure isolation before transaction begin/autobegin, read revision and all persisted ACTIVE rows from one view, and never wall-clock-filter ACTIVE rows in the snapshot query.
- [ ] Run the focused snapshot tests.

### Task 6: Add authenticated snapshot API tests and implementation

**Files:**
- Modify: `web_app/config.py`
- Modify: `web_app/presentation/app.py`
- Create or modify: `web_app/presentation/api/waf_enforcement_router.py`
- Create: `tests/unit/test_pr7_waf_snapshot_route.py`
- Modify: `tests/integration/test_api.py` or the established route fixture.

- [ ] Test disabled 404, missing/wrong bearer 401, valid 200, `Cache-Control: no-store`, safe 503, exact schema, token redaction, and encoded-body ceiling at 1 MiB.
- [ ] Add only the required server-only configuration for controlled-local enablement and `WAF_STATE_SYNC_API_KEY`; preserve existing environment validation.
- [ ] Add thin route wiring with constant-time comparison, typed response, bounded encoded body, safe error handling, and no token/body logging.
- [ ] Run focused API tests.

### Task 7: Run complete Block 1 validation and review diff

**Files:** Changed files only; no runtime WAF files.

- [ ] Run migration upgrade, downgrade, and re-upgrade against disposable/local PostgreSQL; confirm exactly one head.
- [ ] Run the complete Block 1 suite, existing recommendation tests, PR5 tests, PR6 tests, affected backend tests, lint/type/static checks, `git diff --check`, and changed-file secret scan.
- [ ] Review `git diff` for unrelated frontend/ML/runtime changes and confirm real Supabase was untouched.
- [ ] Create clean commits on `feat/pr7-critical-waf-enforcement` only after all required gates pass.
- [ ] Report `BLOCK 1: COMPLETE` only if every gate passes; otherwise report `BLOCK 1: BLOCKED` with the exact invariant and stop before Block 2.
