import json
import logging
from pathlib import Path
from typing import Any

from ml_model.models.mock_model import MockInjectionClassifier
from web_app.config import Settings

logger = logging.getLogger(__name__)

TEMPERATURE = 0.596868


class ModelService:
    MODEL_KEY = "distilbert"
    CHECKPOINT_NAME = f"best_{MODEL_KEY}_ckpt.pt"
    MOCK_MODEL_VERSION = "mock-model-service"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cpu"
        self.model: Any = None
        self.tokenizer: Any = None
        self.temperature = float(TEMPERATURE)
        self.model_version = ""
        self._mock_classifier: MockInjectionClassifier | None = None

        run_dir, was_inferred = self._resolve_run_directory(
            settings,
            Path(settings.model_registry_path).expanduser()
        )
        if was_inferred:
            logger.warning(
                "MODEL_REGISTRY_PATH '%s' resolved to explicit run '%s' for %s mode",
                settings.model_registry_path,
                run_dir,
                settings.app_env,
            )

        try:
            model, tokenizer, loaded_temperature = self._load_run_artifacts(run_dir)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load DistilBERT artifact from '{settings.model_registry_path}': {exc}"
            ) from exc

        self.model = model
        self.tokenizer = tokenizer
        self.temperature = float(loaded_temperature or TEMPERATURE)
        self.model_version = self._derive_model_version(run_dir)

    @classmethod
    def create_mock(cls) -> "ModelService":
        logger.warning(
            "Using mock ModelService for development/testing only. "
            "Real registry artifacts were not loaded."
        )
        instance = cls.__new__(cls)
        instance.settings = None
        instance.device = "cpu"
        instance.model = None
        instance.tokenizer = None
        instance.temperature = float(TEMPERATURE)
        instance.model_version = cls.MOCK_MODEL_VERSION
        instance._mock_classifier = MockInjectionClassifier()
        return instance

    def predict(self, payload: str) -> dict[str, Any]:
        text = payload if isinstance(payload, str) else "" if payload is None else str(payload)

        if self._mock_classifier is not None:
            mock_result = self._mock_classifier.predict(text)
            return self._build_response(
                prediction=mock_result["class"],
                confidence=float(mock_result["confidence"]),
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
            inference_latency_ms=float(result.get("latency_ms", 0.0)),
        )

    @classmethod
    def _resolve_run_directory(
        cls,
        settings: Settings,
        registry_path: Path,
    ) -> tuple[Path, bool]:
        if not registry_path.exists():
            raise FileNotFoundError(
                f"MODEL_REGISTRY_PATH '{registry_path}' does not exist"
            )
        if registry_path.is_file():
            raise FileNotFoundError(
                f"MODEL_REGISTRY_PATH '{registry_path}' must be a directory"
            )

        if cls._is_run_directory(registry_path):
            return registry_path, False

        staging_dir = registry_path
        if (registry_path / "staging").is_dir():
            staging_dir = registry_path / "staging"

        if not (settings.is_development or settings.is_testing):
            raise RuntimeError(
                "MODEL_REGISTRY_PATH must point to an explicit model run directory "
                f"in {settings.app_env} mode; got '{registry_path}'."
            )

        run_dir = cls._discover_latest_run(staging_dir)
        return run_dir, True

    @classmethod
    def _discover_latest_run(cls, staging_dir: Path) -> Path:
        candidates = sorted(
            [
                path
                for path in staging_dir.iterdir()
                if path.is_dir() and path.name.startswith(f"{cls.MODEL_KEY}_")
            ],
            key=lambda path: path.name,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(
                f"No staged '{cls.MODEL_KEY}' artifact found under '{staging_dir}'"
            )
        return candidates[0]

    @classmethod
    def _is_run_directory(cls, path: Path) -> bool:
        return path.name.startswith(f"{cls.MODEL_KEY}_") and (
            (path / "config.json").exists() or (path / cls.CHECKPOINT_NAME).exists()
        )

    @classmethod
    def _derive_model_version(cls, run_dir: Path) -> str:
        config_path = run_dir / "config_used.json"
        if config_path.exists():
            try:
                metadata = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}
            for key in ("model_version", "version", "run_dir", "artifact_version"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return run_dir.name

    def _load_run_artifacts(self, run_dir: Path) -> tuple[Any, Any, float]:
        from ml_model.inference.predict_attack import load_model

        return load_model(
            self.MODEL_KEY,
            staging_dir=run_dir,
            device=self.device,
        )

    def _build_response(
        self,
        *,
        prediction: str,
        confidence: float,
        inference_latency_ms: float,
    ) -> dict[str, Any]:
        confidence_tier = self._confidence_tier_for(confidence)
        response = {
            "prediction": prediction,
            "confidence": round(float(confidence), 6),
            "confidence_tier": confidence_tier,
            "inference_latency_ms": round(float(inference_latency_ms), 3),
            "model_version": self.model_version,
        }
        # TODO: Remove these compatibility aliases once TriageUseCase consumes
        # prediction/confidence_tier directly.
        response["class"] = prediction
        response["confidence_level"] = confidence_tier
        return response

    @staticmethod
    def _confidence_tier_for(confidence: float) -> str:
        if confidence < 0.50:
            return "LOW"
        if confidence < 0.80:
            return "MEDIUM"
        return "HIGH"
