# web_app/application/
#
# Layer: Application (Use Cases)
# Architectural Role: Orchestrates domain objects to fulfill system-level use cases.
# Does NOT depend on FastAPI, PostgreSQL, or any concrete infrastructure detail.
# Depends ONLY on domain/ interfaces and abstractions.
#
# Contents (to be implemented):
#   - TriageUseCase          : coordinates CRS decision + ML inference + confidence gate
#   - AlertLoggingUseCase    : handles persisting security decisions as audit records
#   - RetrainingTriggerUseCase : evaluates drift metrics and initiates retraining pipeline
#   - RollbackUseCase        : promotes previous production model on failure condition
#
# Dependency Rule: imports from domain/ only. Never imports from infrastructure/ or presentation/.
