import json
import logging
from pathlib import Path
from typing import Any, Optional

from ml_model.models.mock_model import MockInjectionClassifier
from web_app.config import Settings

logger = logging.getLogger(__name__)

TEMPERATURE = 0.596868


class ModelService:
    MODEL_KEY = "distilbert"
    CHECKPOINT_NAME = f"best_{MODEL_KEY}_ckpt.pt"
    MOCK_MODEL_VERSION = "mock-model-service"
    DEFAULT_CONFIDENCE_LOW_THRESHOLD = 0.50
    DEFAULT_CONFIDENCE_HIGH_THRESHOLD = 0.80

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cpu"
        self.model: Any = None
        self.tokenizer: Any = None
        self.temperature = float(TEMPERATURE)
        self.model_version = ""
        self._mock_classifier: MockInjectionClassifier | None = None
        self._total_processed = 0
        self._total_inference_latency_ms = 0.0
        self._confidence_low_threshold = float(settings.confidence_low_threshold)
        self._confidence_high_threshold = float(settings.confidence_high_threshold)
        self._eval_metadata: dict[str, Any] = {}

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
        self._eval_metadata = self._load_eval_metadata(run_dir)

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
        instance._total_processed = 0
        instance._total_inference_latency_ms = 0.0
        instance._confidence_low_threshold = cls.DEFAULT_CONFIDENCE_LOW_THRESHOLD
        instance._confidence_high_threshold = cls.DEFAULT_CONFIDENCE_HIGH_THRESHOLD
        instance._eval_metadata = {}
        return instance

    def predict(self, payload: str) -> dict[str, Any]:
        text = payload if isinstance(payload, str) else "" if payload is None else str(payload)

        if self._mock_classifier is not None:
            mock_result = self._mock_classifier.predict(text)
            response = self._build_response(
                prediction=mock_result["class"],
                confidence=float(mock_result["confidence"]),
                inference_latency_ms=0.0,
            )
            self._record_inference(response["inference_latency_ms"])
            return response

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

        response = self._build_response(
            prediction=result["label"],
            confidence=float(result["max_prob"]),
            inference_latency_ms=float(result.get("latency_ms", 0.0)),
        )
        self._record_inference(response["inference_latency_ms"])
        return response

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

    def _record_inference(self, inference_latency_ms: float) -> None:
        self._total_processed += 1
        self._total_inference_latency_ms += float(inference_latency_ms)

    @property
    def loaded(self) -> bool:
        return self.model is not None or self._mock_classifier is not None

    @property
    def is_mock(self) -> bool:
        return self._mock_classifier is not None

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def avg_inference_latency_ms(self) -> float:
        if self._total_processed == 0:
            return 0.0
        return round(self._total_inference_latency_ms / self._total_processed, 3)

    @property
    def confidence_thresholds(self) -> dict[str, float]:
        return {
            "low": self._confidence_low_threshold,
            "high": self._confidence_high_threshold,
        }

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Evaluation metrics from model registry artifact (macro_f1, ece, per_class_f1, etc.)."""
        return self._eval_metadata.copy()

    def _load_eval_metadata(self, run_dir: Path) -> dict[str, Any]:
        """Load evaluation metrics from model registry eval JSON if present."""
        import json

        eval_dir = run_dir / "eval"
        if not eval_dir.is_dir():
            return {}

        # Find the most recent eval file (format: YYYYMMDD_HHMMSS_metrics.json)
        candidates = sorted(
            [
                path
                for path in eval_dir.iterdir()
                if path.is_file() and path.name.endswith("_metrics.json")
            ],
            key=lambda p: p.name,
            reverse=True,
        )
        if not candidates:
            return {}

        metrics_path = candidates[0]
        try:
            raw = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        # Extract fields aligned with backend schema (MLHealthResponse)
        metadata: dict[str, Any] = {}
        if "macro_f1" in raw:
            metadata["macro_f1"] = float(raw["macro_f1"])
        if "ece" in raw:
            metadata["ece"] = float(raw["ece"])
        if "per_class_f1" in raw and isinstance(raw["per_class_f1"], dict):
            metadata["per_class_f1"] = {
                k: float(v) for k, v in raw["per_class_f1"].items()
            }
        if "calibration_bins" in raw and isinstance(raw["calibration_bins"], list):
            metadata["calibration_bins"] = [
                {
                    "bin_idx": int(b.get("bin_idx", i)),
                    "bin_center": float(b["bin_center"]),
                    "accuracy": float(b["accuracy"]),
                    "confidence": float(b["confidence"]),
                    "count": int(b["count"]),
                }
                for i, b in enumerate(raw["calibration_bins"])
                if isinstance(b, dict)
            ]
        if "prediction_distribution" in raw and isinstance(
            raw["prediction_distribution"], dict
        ):
            metadata["prediction_distribution"] = {
                k: int(v) for k, v in raw["prediction_distribution"].items()
            }
        return metadata

    @staticmethod
    def _confidence_tier_for(confidence: float) -> str:
        if confidence < 0.50:
            return "LOW"
        if confidence < 0.80:
            return "MEDIUM"
        return "HIGH"
