# Session Context Block

This file moved from the repo root to `docs/project-ops/` as part of the repo cleanup.

## Domain-Specific Decisions

- **Alert contract:** backend field is `alert_id`, not `traffic_id`. Frontend expects paginated `{ items, total, page, pageSize }` — not a flat list.
- **Model registry:** active path is `ml_model/model_registry/`.
- **Data pipeline limits:** Data pipeline scripts hardcode `G:\Documents\PDDDD\` — do not treat them as repo-relative yet.
