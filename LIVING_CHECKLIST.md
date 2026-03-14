LIVING CHECKLIST
================

Last updated: 2026-03-14

Status summary
--------------
- **Verify staged artifact loads:** Completed
- **Inspect database schema and missing columns:** Completed
- **Add missing ORM columns (nullable-first):** Completed
- **Bootstrap Alembic config/files:** Completed
- **Generate and review migration (cross-dialect):** Completed
- **Apply migration and run tests (local validation):** Completed
- **Swap mock model for real DistilBERT wiring:** Completed
- **Run backend regression tests after model wiring:** Completed
- **Report results and checklist updates:** Completed

Notes
-----
- Frontend fixes were implemented on branch `fix/mark-frontend-corrections` and pushed; PR #31 opened.
- Model artifact loading verified inside project venv (DistilBERT load OK).
- ORM changes made to `web_app/infrastructure/database/database.py` to add the requested nullable columns.
- Alembic scaffold and migration revision `20260314_000001_add_missing_traffic_log_columns.py` created and patched for SQLite validation.
- Migration applied successfully against a local SQLite baseline and legacy-schema snapshot; backend tests passed locally.
- Migration has not been applied to the remote/production database due to DB connectivity/ops constraints; do not run production migration without backup and committing migration + ORM together.
- Real DistilBERT loading is now wired through `web_app/services/model_service.py` and FastAPI lifespan in `web_app/presentation/app.py`.
- `web_app/config.py` now carries `MODEL_REGISTRY_PATH`, environment-aware development fallback behavior, and the locked inference constants/default metadata.
- Dev/test with missing artifact path now logs an explicit warning and uses a mock `ModelService`; non-dev fails fast with a descriptive runtime error.
- The current route/use-case stack still expects legacy classifier keys, so `ModelService.predict()` returns both the new ML payload fields and compatibility keys while leaving action policy in `TriageUseCase`.
- Regression suite result after DistilBERT wiring: `35 passed`.

Next actions (recommended)
-------------------------
- Commit and push the backend changes for DistilBERT wiring on a feature branch and open a PR for review.
- Migrate route/use-case consumers from the legacy classifier key names to the new `prediction` / `confidence_tier` contract when broader backend changes are in scope.
- After PR merge, schedule applying the existing database migration to the target DB with backups and a maintenance window.
- Optionally merge the existing frontend PR if desired.
