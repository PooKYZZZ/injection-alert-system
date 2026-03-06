"""
web_app/application/triage_use_case.py

Application-layer use case for triaging HTTP requests.

Architectural role:
  - Orchestrates the ML inference + confidence-gated action + persistence workflow
  - Depends on domain interfaces (ITrafficLogRepository) only
  - Does NOT depend on FastAPI, SQLAlchemy, or any concrete infrastructure

Dependency rule:
  - Imports from domain/ (entities, interfaces)
  - Does NOT import from infrastructure/ or presentation/
"""

from dataclasses import dataclass
from typing import Protocol

from web_app.domain.interfaces import ITrafficLogRepository, TrafficLogEntity


class IClassifier(Protocol):
    """Protocol for any classifier that can predict on an HTTP request string."""

    def predict(self, http_request: str) -> dict:
        """Return dict with keys: class, confidence, confidence_level."""
        ...


@dataclass
class TriageResult:
    """Value object returned by the triage use case."""

    class_label: str
    confidence: float
    confidence_level: str
    action_taken: str


class TriageUseCase:
    """Coordinates ML inference → confidence-gated action → persistence.

    This use case encapsulates the core business logic:
      1. Run the classifier on the HTTP request
      2. Determine action (BLOCKED / THROTTLED / ALLOWED) based on confidence level
      3. Persist the audit record via the repository interface

    The confidence-gate semantics are:
      - HIGH confidence + attack class → BLOCKED
      - MEDIUM confidence → THROTTLED
      - Otherwise → ALLOWED
    """

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
    ):
        self._classifier = classifier
        self._repository = repository

    async def execute(
        self,
        http_request: str,
        source_ip: str,
    ) -> TriageResult:
        """Run the full triage pipeline and persist the result."""
        # Step 1 — ML inference
        result = self._classifier.predict(http_request)

        # Step 2 — Confidence-gated action decision
        if result["confidence_level"] == "HIGH" and result["class"] != "Normal":
            action_taken = "BLOCKED"
        elif result["confidence_level"] == "MEDIUM":
            action_taken = "THROTTLED"
        else:
            action_taken = "ALLOWED"

        # Step 3 — Persist audit record via repository
        entity = TrafficLogEntity(
            source_ip=source_ip,
            http_request=http_request,
            prediction=result["class"],
            confidence=result["confidence"],
            confidence_level=result["confidence_level"],
            action_taken=action_taken,
        )
        # TODO: Consider exposing the saved entity ID in TriageResult for future
        # feedback linking (e.g., client can reference the audit record directly).
        # Currently the return value is ignored - uncomment below when needed:
        # saved_entity = await self._repository.save(entity)
        await self._repository.save(entity)

        return TriageResult(
            class_label=result["class"],
            confidence=result["confidence"],
            confidence_level=result["confidence_level"],
            action_taken=action_taken,
        )
