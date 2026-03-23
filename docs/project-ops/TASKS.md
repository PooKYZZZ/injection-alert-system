# TASKS.md — Injection Alert System
# Current Atomic Task List (Merge + Defense Track)

**Last updated:** 2026-03-23  
**Linked plan:** `docs/project-ops/IMPLEMENTATION_PLAN.md`

---

## Usage

1. Read `AGENTS.md`.
2. Read `docs/project-ops/STATUS.md`.
3. Execute the first `[ ]` task in order.
4. Run all verify commands for that task.
5. Mark the task `[x]` only when verification is green.

Status legend:

```text
[ ] Not started
[~] In progress
[x] Done and verified
[!] Blocked
```

---

## Phase 1 — Core Merge Gate

### Task 1.1 — Backend Python 3.14 gate

**Status:** `[ ]`  
**Goal:** Confirm backend passes on Python 3.14 venv.

Verify:

```powershell
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q
```

Acceptance:
- Python reports 3.14.x.
- `pip check` passes.
- pytest passes.

---

### Task 1.2 — Frontend static and BFF gate

**Status:** `[ ]`  
**Goal:** Confirm frontend checks pass with current runner settings.

Verify:

```powershell
cd frontend
npm run typecheck
npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts
npm run build
```

Acceptance:
- Typecheck passes.
- BFF-focused tests pass.
- Production build passes.

---

### Task 1.3 — CI parity sanity

**Status:** `[ ]`  
**Goal:** Ensure branch CI and local gate results are consistent.

Verify:

- Confirm latest `frontend-adaptation` push has green backend and frontend checks.
- If CI fails, capture failing step and create a focused fix task before merge.

Acceptance:
- No unresolved CI failures for backend/frontend check jobs.

---

## Phase 2 — Operator Doc Lock

### Task 2.1 — Status doc lock

**Status:** `[ ]`  
**Files:** `docs/project-ops/STATUS.md`

Goal:
- Keep stack versions, test baselines, and route reality current.
- Keep this file short and operational.

Acceptance:
- No stale test counts or deprecated file references.

---

### Task 2.2 — Plan/task doc lock

**Status:** `[ ]`  
**Files:** `docs/project-ops/IMPLEMENTATION_PLAN.md`, `docs/project-ops/TASKS.md`

Goal:
- Keep plan/task docs aligned to current repo and immediate merge priorities.
- Remove stale references (for example old `middleware.ts` references).

Acceptance:
- Docs reflect `frontend/proxy.ts` and current verification commands.

---

### Task 2.3 — Setup/readme consistency check

**Status:** `[ ]`  
**Files:** `README.md`, `docs/SETUP.md`, `docs/CONTEXT.md`

Goal:
- Ensure commands and env guidance are consistent across operator-facing docs.

Acceptance:
- No conflicting command variants for the core gate.
- Env variable guidance is consistent (`AUTH_SECRET`, internal API key matching).

---

## Phase 3 — Pre-Master Merge Actions

### Task 3.1 — Merge candidate checklist

**Status:** `[ ]`

Checklist:
- [ ] Working tree is clean on `frontend-adaptation`.
- [ ] Core merge gate tasks are `[x]`.
- [ ] CI checks are green.
- [ ] No pending blockers in STATUS open gaps that impact merge safety.

Acceptance:
- Branch is ready for merge to `master`.

---

### Task 3.2 — Post-merge follow-up backlog draft

**Status:** `[ ]`

Goal:
- Create a short deferred backlog (Docker/ModSecurity rollout, optional CI trigger optimization, Supabase operational tasks) after merge.

Acceptance:
- Deferred work is explicit and not mixed into merge-critical tasks.

---

## Completion Criteria

```text
[ ] Task 1.1 complete
[ ] Task 1.2 complete
[ ] Task 1.3 complete
[ ] Task 2.1 complete
[ ] Task 2.2 complete
[ ] Task 2.3 complete
[ ] Task 3.1 complete
[ ] Task 3.2 complete
```
