# Contributing

Last updated: 2026-03-20

This repo follows a docs-as-code workflow. Keep documentation, code, and validation steps aligned in the same change set.

## Workflow

- Create a branch from the current base branch
- Use branch names in this form:
  - `feat/<scope>`
  - `fix/<scope>`
- Keep commits focused
- If behavior, setup, or architecture changes, update the matching document in `docs/`

## Before Opening A PR

Run the checks that match the area you touched:

```powershell
# Backend
.venv\Scripts\python.exe -m pytest -q

# Frontend
cd frontend
npm run typecheck

# Frontend tests (full suite)
cd frontend
npx vitest run
```

Optional but recommended when relevant:

```powershell
# Python formatting / lint
python -m black .
python -m ruff check .

# Frontend tests (focused BFF tests)
cd frontend
npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts
```

## Current Test Baseline (2026-03-20)

| Test Suite | Result |
|------------|--------|
| pytest | 87 passed |
| typecheck | PASSED |
| vitest (full) | 74 passed |

## Architecture Guardrails

- Keep the BFF pattern intact:
  - `Browser -> Next.js Route Handler -> FastAPI`
- Keep business logic out of route handlers
- Use Zod for BFF payload validation
- Use async database drivers only
- Keep secrets in `.env` files only
- Do not hardcode API keys, tokens, or local secrets
- Do not write to `ml_model/model_registry/production/` from the web app
- Do not casually modify `data/processed/v3_907k_cleaned/`

## Confidence Gate Guardrail

Do not change the confidence thresholds without explicit approval:

- `HIGH > 80%`
- `MEDIUM 50% to 80%`
- `LOW < 50%`

## Documentation Expectations

- Document current behavior, not intent
- If a feature is partial or mock-backed, say so directly
- Keep setup instructions runnable on the current repo
- Preserve academic documents, but clearly separate them from implementation-status docs

## Sensitive Data

Never commit:

- `.env`
- `.env.local`
- live API keys
- production secrets
- service-role credentials
