# web_app/application/
#
# Layer: Application (Use Cases)
# Architectural Role: Orchestrates domain objects to fulfill system-level use cases.
# Does NOT depend on FastAPI, PostgreSQL, or any concrete infrastructure detail.
# Depends ONLY on domain/ interfaces and abstractions.
#
# Contents:
#   - triage_use_case.py       : coordinates CRS decision + ML inference + confidence gate
#   - feedback_use_case.py     : handles analyst feedback persistence
#   - (planned) alert_logging_use_case.py : audit record management
#   - (planned) retraining_trigger_use_case.py : drift metrics → retrain pipeline
#   - (planned) rollback_use_case.py : model rollback on failure
#
# Service responsibilities absorbed from web_app/services/:
#   - Log bridge (ModSecurity audit log ingestion) → implement as a use case here
#   - Mitigation orchestrator (confidence-gated enforcement) → triage_use_case.py
#   - Model lifecycle (loading, version selection) → presentation/app.py singleton + infra adapter
#
# Dependency Rule: imports from domain/ only. Never imports from infrastructure/ or presentation/.
