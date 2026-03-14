import logging
from pathlib import Path
from typing import Any

from ml_model.models.mock_model import MockInjectionClassifier
from web_app.config import Settings

logger = logging.getLogger(__name__)


class ModelService:
    MODEL_KEY = "distilbert"
    CHECKPOINT_NAME = f"best_{MODEL_KEY}_ckpt.pt"
    MOCK_MODEL_VERSION = "mock-model-service"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cpu"
        self.model: Any = None
        self.tokenizer: Any = None
        self.model_version = settings.model_version
        self.temperature = settings.temperature
        self._mock_classifier: MockInjectionClassifier | None = None

        registry_path = Path(settings.model_registry_path).expanduser()
        load_target, model_version = self._resolve_load_target(registry_path)

        try:
            from ml_model.inference.predict_attack import load_model

            model, tokenizer, loaded_temperature = load_model(
                self.MODEL_KEY,
                staging_dir=str(load_target),
                device=self.device,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load DistilBERT artifact from '{settings.model_registry_path}': {exc}"
            ) from exc

        self.model = model
        self.tokenizer = tokenizer
        self.model_version = model_version
        if loaded_temperature is not None:
            self.temperature = float(loaded_temperature)

    @classmethod
    def create_mock(cls) -> "ModelService":
        logger.warning("Using mock ModelService — real artifact not loaded")
        instance = cls.__new__(cls)
        instance.settings = None
        instance.device = "cpu"
        instance.model = None
        instance.tokenizer = None
        instance.model_version = cls.MOCK_MODEL_VERSION
        instance.temperature = 1.0
        instance._mock_classifier = MockInjectionClassifier()
        return instance

    def predict(self, payload: str) -> dict:
        text = payload if isinstance(payload, str) else "" if payload is None else str(payload)

        if self._mock_classifier is not None:
            mock_result = self._mock_classifier.predict(text)
            return self._build_response(
                prediction=mock_result["class"],
                confidence=float(mock_result["confidence"]),
                confidence_tier=mock_result["confidence_level"],
                inference_latency_ms=0.0,
            )

        try:
            from ml_model.inference.predict_attack import predict_attack

            result = predict_attack(
                text,
                self.model,
                self.tokenizer,
                device=self.device,
                temperature=self.temperature,
                return_latency=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"ModelService prediction failed for model '{self.model_version}': {exc}"
            ) from exc

        return self._build_response(
            prediction=result["label"],
            confidence=float(result["max_prob"]),
            confidence_tier=result["tier"],
            inference_latency_ms=float(result.get("latency_ms", 0.0)),
        )

    @classmethod
    def _resolve_load_target(cls, registry_path: Path) -> tuple[Path, str]:
        if not registry_path.exists():
            raise FileNotFoundError(f"MODEL_REGISTRY_PATH '{registry_path}' does not exist")
        if registry_path.is_file():
            raise FileNotFoundError(f"MODEL_REGISTRY_PATH '{registry_path}' must be a directory")
        if cls._is_run_directory(registry_path):
            return registry_path.parent, registry_path.name

        candidates = sorted(
            [
                child
                for child in registry_path.iterdir()
                if child.is_dir() and child.name.startswith(f"{cls.MODEL_KEY}_")
            ],
            key=lambda path: path.name,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(
                f"No staged '{cls.MODEL_KEY}' artifact found under '{registry_path}'"
            )
        return registry_path, candidates[0].name

    @classmethod
    def _is_run_directory(cls, path: Path) -> bool:
        return path.name.startswith(f"{cls.MODEL_KEY}_") and (path / cls.CHECKPOINT_NAME).exists()

    def _build_response(
        self,
        *,
        prediction: str,
        confidence: float,
        confidence_tier: str,
        inference_latency_ms: float,
    ) -> dict:
        return {
            "prediction": prediction,
            "confidence": round(float(confidence), 6),
            "confidence_tier": confidence_tier,
            "inference_latency_ms": round(float(inference_latency_ms), 3),
            "model_version": self.model_version,
            "class": prediction,
            "confidence_level": confidence_tier,
        }
