# AGENTS.md — Injection Alert System

Injection Alert System is an academic capstone repository for SQL injection detection and analyst triage. The current repo contains a FastAPI backend, a Next.js dashboard BFF, and transformer-based ML artifacts for a CRS-first WAF-plus-ML workflow. It is not yet the full Docker/ModSecurity/Redis/Supabase deployment target.

## Stack

- Frontend: Next.js `15.2.3`, React `19`, TypeScript `5.9`, Auth.js / NextAuth `5.0.0-beta.30`, TanStack Query `5`, Zustand `5`, Zod `3`, Tailwind CSS `4`
- Backend: Python `3.10+`, FastAPI `>=0.104,<1`, Pydantic `2`, async SQLAlchemy `2`
- ML: PyTorch `2.x`, Hugging Face Transformers `4.x`
- Data: SQLite for tests/local work, PostgreSQL as the async runtime target, Supabase as the planned production boundary
- Model artifacts: `ml_model/model_registry/`

## Commands

```powershell
# Backend
.venv\Scripts\python.exe -m pytest -q
uvicorn web_app.presentation.app:create_app --reload

# Frontend
cd frontend
npm run dev
npm run typecheck
npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts
```

## Hard Rules

- Do not change the confidence thresholds without explicit approval:
  - `HIGH` `> 80%`
  - `MEDIUM` `50–80%`
  - `LOW` `< 50%`
- Preserve the current backend transport contract for `action_taken`: `BLOCKED`, `THROTTLED`, `ALLOWED`.
- If `ALLOWED` is ever renamed to `LOGGED`, make that change in backend policy code first, then propagate it through frontend contracts, schemas, mocks, and BFF code.
- Keep secrets only in `.env` or `.env.local`. Never hardcode tokens, keys, or service credentials.
- Never commit `.env`, `.env.local`, live API keys, or service-role credentials.
- Never let the browser call FastAPI directly. Keep the boundary `Browser -> Next.js Route Handler -> FastAPI`.
- Do not write to `ml_model/model_registry/production/` from the web app.
- Do not casually modify `data/processed/v3_907k_cleaned/`.
- Do not add sync SQLAlchemy drivers or sync DB access paths.
- Do not add `UPDATE` or `DELETE` behavior to the audit-log style traffic data model without explicit approval.

## Architecture Boundaries

- Backend layering is `domain -> application -> infrastructure -> presentation`. Keep dependencies flowing inward.
- Route handlers stay thin. Business logic belongs in use cases, services, or repositories, not in FastAPI or Next.js route files.
- `web_app.presentation.app:create_app` is the FastAPI entrypoint.
- `app.state.model` is a compatibility alias for `app.state.model_service`; do not remove it until all call sites are migrated.
- Any async path that calls `model_service.predict()` must use `await run_in_threadpool(model_service.predict, payload)`.
- The runtime model boundary is `web_app/services/model_service.py`.
- The frontend alert contract source of truth is `frontend/features/alerts/contract.ts`.
- Validate BFF payloads with Zod.
- `USE_MOCK_API` is the centralized server-only mock toggle for the dashboard BFF routes.
- Next.js -> FastAPI internal calls use `Authorization: Bearer <INTERNAL_API_KEY>`, which must match backend `API_SECRET_KEY`.

## Workflow And Verification

- Prefer small, targeted changes that preserve current contracts.
- Add or update tests with backend behavior changes, especially for routes, auth, persistence, and triage behavior.
- Run the checks for the area you touched before finishing:
  - Backend: `.venv\Scripts\python.exe -m pytest -q`
  - Frontend: `cd frontend && npm run typecheck`
  - BFF work: `cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts`
- If behavior, setup, or architecture changes, update the matching docs in `docs/`.
- If you edit operator-facing status or handoff material, keep `docs/project-ops/STATUS.md` and `docs/project-ops/LIVING_CHECKLIST.md` aligned with the code.
- Use `feat/<scope>` or `fix/<scope>` branch names.
- PR descriptions should reference the relevant item in `docs/project-ops/LIVING_CHECKLIST.md`.

## Session Start

Read these first unless the task is narrowly scoped:

1. `AGENTS.md`
2. `docs/project-ops/STATUS.md`
3. `docs/project-ops/LIVING_CHECKLIST.md`
4. `docs/README.md`

Then stop broad doc reading and move to the specific code paths for the task.

## Stable Guidance

- Treat `docs/CONTEXT.md`, `docs/architecture.md`, and `docs/SETUP.md` as the current implementation docs.
- Detailed MCP and CLI routing guidance lives in `docs/agent-tooling.md`.
- Read `docs/agent-tooling.md` when the task involves tool selection, MCP vs CLI decisions, browser automation, library or framework docs lookup, GitHub release/PR/issue work, or large outputs such as logs, JSON, Markdown, and fetched pages.
- Do not read `docs/agent-tooling.md` by default for narrow code fixes unless tool choice is central to the task.
- Treat `docs/feasibility_report.md` and other thesis material as design context, not runtime truth.
- Do not document planned infrastructure as if it already ships in this repo.
