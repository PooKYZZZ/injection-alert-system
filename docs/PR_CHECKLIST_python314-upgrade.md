# Python 3.14 Upgrade PR Summary

## Scope

This branch raises the repository baseline to Python 3.14 and updates the dependency stack to the latest stable releases that still support the project.

## What Changed

- Backend runtime baseline updated to Python 3.14
- Backend dependency pins refreshed to 3.14-compatible latest stable releases
- Frontend dependency pins refreshed to current compatible releases
- CI updated to run the backend on Python 3.14
- Docs and setup notes updated to match the new baseline

## Verification

- `uv pip install -r requirements.txt`
- `uv pip install -r requirements.train.txt`
- `.venv\Scripts\python.exe -m pytest -q` → `259 passed`
- `cd frontend && npm run lint` → passed
- `cd frontend && npm run typecheck` → passed
- `cd frontend && npx vitest run` → `107 passed`

## Known Constraint

- `next-auth` remains on `5.0.0-beta.30`
- The stable `next-auth` line is a different major path, so moving away from the beta would require a dedicated auth migration and is intentionally out of scope for this upgrade pass

## Follow-Up Split

- Frontend lint cleanup was handled as a separate follow-on pass so this upgrade PR stays focused on the runtime and dependency migration

