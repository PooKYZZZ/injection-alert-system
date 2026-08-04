import json
import logging
from pathlib import Path
from typing import Any

from ml_model.confidence_tiers import (
    ConfidenceThresholds,
    DEFAULT_CONFIDENCE_THRESHOLDS,
    classify_confidence,
)
from ml_model.models.mock_model import MockInjectionClassifier
from ml_model.preprocessing.model_input import (
    LEGACY_MODEL_INPUT_VERSION,
    MODEL_INPUT_VERSION,
    validate_supported_model_input_version,
)
from web_app.config import Settings

logger = logging.getLogger(__name__)

TEMPERATURE = 0.596868


class ModelService:
    MODEL_KEY = "distilbert"
    CHECKPOINT_NAME = f"best_{MODEL_KEY}_ckpt.pt"
    PACKAGED_MANIFEST_NAME = "serving_manifest.json"
    PACKAGED_EVAL_REPORT_NAME = "eval_report.json"
    MOCK_MODEL_VERSION = "mock-model-service"
    DEFAULT_CONFIDENCE_LOW_THRESHOLD = 0.50
    DEFAULT_CONFIDENCE_HIGH_THRESHOLD = 0.80
    DEFAULT_CONFIDENCE_CRITICAL_THRESHOLD = 0.90

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cpu"
        self.model: Any = None
        self.tokenizer: Any = None
        self.temperature = float(TEMPERATURE)
        self.model_version = ""
        self.model_input_version = MODEL_INPUT_VERSION
        self._mock_classifier: MockInjectionClassifier | None = None
        self._total_processed = 0
        self._total_inference_latency_ms = 0.0
        self._confidence_thresholds = ConfidenceThresholds(
            low=float(settings.confidence_low_threshold),
            high=float(settings.confidence_high_threshold),
            critical=float(settings.confidence_critical_threshold),
        )
        self._eval_metadata: dict[str, Any] = {}

        run_dir, was_inferred = self._resolve_run_directory(
            settings, Path(settings.model_registry_path).expanduser()
        )
        if was_inferred:
            logger.warning(
                "MODEL_REGISTRY_PATH '%s' resolved to explicit run '%s' for %s mode",
                settings.model_registry_path,
                run_dir,
                settings.app_env,
            )

        try:
            self.model_input_version = self._validate_model_input_metadata(run_dir)
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
        instance.model_input_version = MODEL_INPUT_VERSION
        instance._mock_classifier = MockInjectionClassifier()
        instance._total_processed = 0
        instance._total_inference_latency_ms = 0.0
        instance._confidence_thresholds = ConfidenceThresholds(
            low=cls.DEFAULT_CONFIDENCE_LOW_THRESHOLD,
            high=cls.DEFAULT_CONFIDENCE_HIGH_THRESHOLD,
            critical=cls.DEFAULT_CONFIDENCE_CRITICAL_THRESHOLD,
        )
        instance._eval_metadata = {}
        return instance

    def predict(self, payload: str) -> dict[str, Any]:
        text = (
            payload
            if isinstance(payload, str)
            else ""
            if payload is None
            else str(payload)
        )

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
                confidence_thresholds=self._confidence_thresholds,
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

        if cls._is_artifact_directory(registry_path):
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
    def _is_packaged_artifact_directory(cls, path: Path) -> bool:
        return path.is_dir() and (
            (path / cls.PACKAGED_MANIFEST_NAME).exists()
            or ((path / "config.json").exists() and (path / "tokenizer.json").exists())
        )

    @classmethod
    def _is_artifact_directory(cls, path: Path) -> bool:
        return cls._is_run_directory(path) or cls._is_packaged_artifact_directory(path)

    @classmethod
    def _derive_model_version(cls, run_dir: Path) -> str:
        manifest_path = run_dir / cls.PACKAGED_MANIFEST_NAME
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
            for key in ("model_version", "run_dir_name", "artifact_version"):
                value = manifest.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

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

    @classmethod
    def _validate_model_input_metadata(cls, run_dir: Path) -> str:
        """Validate explicit v2 metadata or the documented known v1 run rule."""

        candidates = [run_dir / "config_used.json", run_dir / cls.PACKAGED_MANIFEST_NAME]
        existing_paths = [path for path in candidates if path.is_file()]
        if not existing_paths:
            raise ValueError(
                "model artifact is missing preprocessing_version metadata; "
                f"expected {MODEL_INPUT_VERSION!r}"
            )
        metadata: dict[str, Any] = {}
        for metadata_path in existing_paths:
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid model metadata: {metadata_path}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"invalid model metadata object: {metadata_path}")
            metadata.update(payload)
        declared_version = metadata.get("preprocessing_version")
        if declared_version is not None:
            return validate_supported_model_input_version(
                declared_version, context=f"model artifact {existing_paths[-1].name}"
            )

        # Legacy compatibility is deliberately narrow: only the existing
        # v3_907k_cleaned artifact contract may omit the new field. Unknown or
        # metadata-less artifacts still fail closed.
        if metadata.get("dataset_version") == "v3_907k_cleaned":
            return LEGACY_MODEL_INPUT_VERSION
        raise ValueError(
            "model artifact is missing preprocessing_version metadata and does not "
            "match the documented v3_907k_cleaned legacy contract"
        )

    def _build_response(
        self,
        *,
        prediction: str,
        confidence: float,
        inference_latency_ms: float,
    ) -> dict[str, Any]:
        confidence_tier = self._confidence_tier_for(
            confidence,
            thresholds=self._confidence_thresholds,
        )
        response = {
            "prediction": prediction,
            "confidence": round(float(confidence), 6),
            "confidence_tier": confidence_tier,
            "inference_latency_ms": round(float(inference_latency_ms), 3),
            "model_version": self.model_version,
        }
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
            "low": self._confidence_thresholds.low,
            "high": self._confidence_thresholds.high,
            "critical": self._confidence_thresholds.critical,
        }

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Evaluation metrics from model registry artifact (macro_f1, ece, per_class_f1, etc.)."""
        return self._eval_metadata.copy()

    def _load_eval_metadata(self, run_dir: Path) -> dict[str, Any]:
        """Load evaluation metrics from model registry calibrated eval JSON.

        The eval pipeline produces files named
        eval_results_{model}_{variant}.json (e.g. eval_results_distilbert_calibrated.json)
        under run_dir/eval/{timestamp}/ directories.

        Supported artifact keys:
            macro_f1, ece, per_class (nested {f1, precision, recall, ...}),
            calibration_bins (nested {bin, avg_conf, avg_acc, gap, count}),
            operational.confidence_tiers ({HIGH/MEDIUM/LOW: {count, ...}}).
        """
        metrics_path = self._find_eval_metrics_path(run_dir)
        if metrics_path is None:
            return {}

        try:
            raw = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            logger.warning("Failed to read eval metadata from %s", metrics_path)
            return {}

        return self._extract_eval_metadata(raw)

    def _find_eval_metrics_path(self, run_dir: Path) -> Path | None:
        eval_dir = run_dir / "eval"
        if eval_dir.is_dir():
            target_name = f"eval_results_{self.MODEL_KEY}_calibrated.json"
            candidates: list[Path] = []
            for child in eval_dir.iterdir():
                if child.is_dir():
                    candidate = child / target_name
                    if candidate.is_file():
                        candidates.append(candidate)
                elif child.is_file() and child.name == target_name:
                    candidates.append(child)

            candidates.sort(key=lambda p: p.parent.name, reverse=True)
            if candidates:
                return candidates[0]

        packaged_report = run_dir / self.PACKAGED_EVAL_REPORT_NAME
        if packaged_report.is_file():
            return packaged_report

        return None

    def _extract_eval_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}

        macro_f1 = raw.get("macro_f1")
        if macro_f1 is None:
            macro_avg = raw.get("macro avg")
            if isinstance(macro_avg, dict):
                macro_f1 = macro_avg.get("f1") or macro_avg.get("f1-score")
        if macro_f1 is not None:
            metadata["macro_f1"] = float(macro_f1)

        if "ece" in raw and raw.get("ece") is not None:
            metadata["ece"] = float(raw["ece"])

        per_class = raw.get("per_class")
        if not isinstance(per_class, dict):
            per_class = {
                label: metrics
                for label, metrics in raw.items()
                if label not in {"accuracy", "macro avg", "weighted avg", "ece", "macro_f1", "calibration_bins", "temperature"}
                and isinstance(metrics, dict)
            }

        if isinstance(per_class, dict):
            metadata["per_class_f1"] = {
                cls_name: float(metrics.get("f1", metrics.get("f1-score")))
                for cls_name, metrics in per_class.items()
                if isinstance(metrics, dict)
                and metrics.get("f1", metrics.get("f1-score")) is not None
            }

            metadata["prediction_distribution"] = {
                cls_name: int(metrics["support"])
                for cls_name, metrics in per_class.items()
                if isinstance(metrics, dict) and "support" in metrics
            }

        # calibration_bins: [{ bin: 0, avg_conf: 0.5, avg_acc: 0.8, gap: 0.01, count: 100 }, ...]
        # → [{ bin_idx: 0, bin_center: 0.5, accuracy: 0.8, confidence: 0.5, count: 100 }, ...]
        raw_bins = raw.get("calibration_bins")
        if isinstance(raw_bins, list):
            metadata["calibration_bins"] = [
                {
                    "bin_idx": int(b.get("bin", i)),
                    "bin_center": float(b.get("avg_conf", 0.0)),
                    "accuracy": float(b.get("avg_acc", 0.0)),
                    "confidence": float(b.get("avg_conf", 0.0)),
                    "count": int(b.get("count", 0)),
                }
                for i, b in enumerate(raw_bins)
                if isinstance(b, dict)
            ]

        return metadata

    @staticmethod
    def _confidence_tier_for(
        confidence: float,
        thresholds: ConfidenceThresholds | None = None,
    ) -> str:
        return classify_confidence(
            confidence,
            thresholds=thresholds or DEFAULT_CONFIDENCE_THRESHOLDS,
        )
