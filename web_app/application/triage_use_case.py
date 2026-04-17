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
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from web_app.application.http_parsing import parse_http_request_line
from web_app.application.http_preprocessor import preprocess_http_request
from web_app.application.waf_event_sanitizer import redact_sensitive_text
from web_app.domain.interfaces import ITrafficLogRepository, TrafficLogEntity


class IClassifier(Protocol):
    """Protocol for any classifier that can predict on an HTTP request string."""

    loaded: bool
    model_version: str

    def predict(self, http_request: str) -> dict:
        """Return dict with prediction + confidence metadata."""
        ...


@dataclass(frozen=True)
class TriageIngestCommand:
    transaction_id: str
    timestamp: datetime
    source_ip: str
    request_method: str
    request_uri: str
    request_headers: dict[str, str]
    request_body: str
    http_request: str
    crs_score: int
    crs_rule_ids: list[str]
    ingest_source: str | None = None
    matched_rule_messages: list[str] | None = None
    matched_rule_tags: list[str] | None = None
    query_string: str | None = None


@dataclass(frozen=True)
class TriageResult:
    """Value object returned by the triage use case."""

    alert_id: int | None
    prediction: str
    confidence: float
    confidence_level: str
    action_taken: str
    model_version: str | None

    @property
    def class_label(self) -> str:
        return self.prediction


class ModelNotReadyError(RuntimeError):
    """Raised when triage is requested while the model service is unavailable."""


class TriageInProgressError(RuntimeError):
    """Raised when another request currently owns the transaction_id claim."""


class TriageUseCase:
    """Coordinates deduplication, ML inference, action policy, and persistence."""

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
        stale_processing_timeout_seconds: int = 30,
        enable_preprocessing: bool = True,
    ):
        self._classifier = classifier
        self._repository = repository
        self._stale_processing_timeout_seconds = stale_processing_timeout_seconds
        self._enable_preprocessing = enable_preprocessing

    async def execute(
        self,
        http_request: str,
        source_ip: str,
    ) -> TriageResult:
        """Legacy execute path used by the existing prediction endpoint.

        Now parses structured request metadata (method, path) from the raw HTTP
        request string to enable analytics like top_targeted_paths.
        """
        prediction = await self._predict(http_request)
        action_taken = self._action_for(
            prediction=prediction["prediction"],
            confidence_level=prediction["confidence_level"],
        )

        # Parse structured request metadata from raw HTTP request
        parsed = parse_http_request_line(http_request)

        saved = await self._repository.save(
            TrafficLogEntity(
                source_ip=source_ip,
                request_method=parsed.method,
                request_path=parsed.path,
                http_request=redact_sensitive_text(http_request),
                prediction=prediction["prediction"],
                confidence=prediction["confidence"],
                confidence_level=prediction["confidence_level"],
                inference_latency_ms=prediction.get("inference_latency_ms"),
                model_version=prediction.get("model_version"),
                action_taken=action_taken,
            )
        )
        return self._result_from_entity(saved)

    async def ingest(self, command: TriageIngestCommand) -> TriageResult:
        now = datetime.now(timezone.utc)
        owner_token = uuid4().hex
        lease_expires_at = now + timedelta(
            seconds=self._stale_processing_timeout_seconds
        )

        authoritative = await self._repository.claim_or_reclaim_processing(
            TrafficLogEntity(
                transaction_id=command.transaction_id,
                timestamp=command.timestamp,
                source_ip=command.source_ip,
                request_path=command.request_uri,
                query_string=command.query_string,
                request_method=command.request_method,
                http_request=self._build_persisted_http_request(command),
                crs_score=command.crs_score,
                crs_rule_ids=command.crs_rule_ids,
                ingest_source=command.ingest_source,
                matched_rule_messages=command.matched_rule_messages,
                matched_rule_tags=command.matched_rule_tags,
                status="PROCESSING",
            ),
            owner_token=owner_token,
            lease_expires_at=lease_expires_at,
            now=now,
        )
        if authoritative is None:
            existing = await self._repository.get_by_transaction_id(
                command.transaction_id
            )
            if existing is None:
                raise RuntimeError(
                    "transaction_id claim was lost but the existing row could not be loaded"
                )
            if existing.status == "COMPLETED":
                return self._result_from_entity(existing)
            if existing.status == "PROCESSING":
                raise TriageInProgressError(
                    "Triage ingest is already processing for this transaction_id"
                )
            raise RuntimeError(
                f"Unsupported triage reservation status '{existing.status}' for transaction_id"
            )

        if authoritative.status == "COMPLETED":
            return self._result_from_entity(authoritative)

        prediction = await self._predict(command.http_request)
        action_taken = self._action_for(
            prediction=prediction["prediction"],
            confidence_level=prediction["confidence_level"],
        )
        saved = await self._repository.complete_processing(
            command.transaction_id,
            owner_token=owner_token,
            prediction=prediction["prediction"],
            confidence=prediction["confidence"],
            confidence_level=prediction["confidence_level"],
            inference_latency_ms=prediction.get("inference_latency_ms"),
            model_version=prediction.get("model_version"),
            action_taken=action_taken,
        )
        return self._result_from_entity(saved)

    async def _predict(self, http_request: str) -> dict:
        if self._classifier is None or not getattr(self._classifier, "loaded", True):
            raise ModelNotReadyError("Model service is unavailable or not ready")

        # Preprocess HTTP request for model input (training-serving consistency)
        # The raw http_request is still persisted verbatim; this only affects
        # the text passed to the ML model.
        model_input = http_request
        if self._enable_preprocessing:
            preprocessed = preprocess_http_request(http_request)
            # Preserve legacy endpoint behavior for payload-only inputs while
            # still using canonicalized text when a valid HTTP request is present.
            if preprocessed:
                model_input = preprocessed

        raw_result = await run_in_threadpool(self._classifier.predict, model_input)
        prediction = raw_result.get("prediction") or raw_result.get("class")
        confidence_level = raw_result.get("confidence_level") or raw_result.get(
            "confidence_tier"
        )
        model_version = raw_result.get("model_version") or getattr(
            self._classifier,
            "model_version",
            None,
        )
        try:
            confidence = float(raw_result["confidence"])
        except (TypeError, ValueError):
            raise ModelNotReadyError(
                "Model returned an invalid prediction payload"
            ) from None
        except KeyError:
            raise ModelNotReadyError(
                "Model returned an invalid prediction payload"
            ) from None

        if not prediction or not confidence_level:
            raise ModelNotReadyError("Model returned an invalid prediction payload")

        return {
            "prediction": prediction,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "inference_latency_ms": raw_result.get("inference_latency_ms"),
            "model_version": model_version,
        }

    @staticmethod
    def _action_for(*, prediction: str, confidence_level: str) -> str:
        if confidence_level == "HIGH" and prediction != "Normal":
            return "BLOCKED"
        if confidence_level == "MEDIUM":
            return "THROTTLED"
        return "ALLOWED"

    @staticmethod
    def _build_persisted_http_request(command: TriageIngestCommand) -> str:
        # Retention decision: request_headers and request_body are accepted for
        # ingest fidelity but folded into the single http_request column.
        # Persist the path-only request line so WAF query strings are not stored
        # in analyst-facing evidence while the classifier can still score them.
        request_line = f"{command.request_method} {command.request_uri} HTTP/1.1"
        header_lines = "\n".join(
            f"{key}: {value}" for key, value in command.request_headers.items()
        )
        parts = [request_line]
        if header_lines:
            parts.append(f"\nHeaders:\n{redact_sensitive_text(header_lines)}")
        if command.request_body:
            parts.append(f"\nBody:\n{redact_sensitive_text(command.request_body)}")
        return "".join(parts)

    @staticmethod
    def _result_from_entity(entity: TrafficLogEntity) -> TriageResult:
        return TriageResult(
            alert_id=entity.id,
            prediction=entity.prediction or "Normal",
            confidence=entity.confidence or 0.0,
            confidence_level=entity.confidence_level or "LOW",
            action_taken=entity.action_taken or "ALLOWED",
            model_version=entity.model_version,
        )
