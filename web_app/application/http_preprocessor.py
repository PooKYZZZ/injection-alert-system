"""Compatibility exports for the shared training/serving model-input contract.

The implementation lives in ``ml_model.preprocessing.model_input`` so the
training pipeline can use the identical code without importing web_app code.
"""

from ml_model.preprocessing.model_input import (
    LEGACY_MODEL_INPUT_VERSION,
    MODEL_INPUT_FALLBACK_VERSION,
    MODEL_INPUT_BUILDER,
    MODEL_INPUT_HASH_POLICY,
    MODEL_INPUT_TEXT_COLUMN,
    MODEL_INPUT_VERSION,
    build_model_input_text,
    canonicalize_text,
    parse_raw_http,
    prepare_model_input,
    prepare_legacy_model_input,
    preprocess_http_request,
    redact_query_string,
    redact_sensitive_text,
    sanitize_model_input_request,
)


def prepare_model_input_for_version(
    raw_http: str, preprocessing_version: str
) -> tuple[str, str, str]:
    if preprocessing_version == MODEL_INPUT_VERSION:
        return prepare_model_input(raw_http)
    if preprocessing_version == "http-preprocessor-v1":
        return prepare_legacy_model_input(raw_http)
    raise ValueError(f"Unsupported model-input version: {preprocessing_version!r}")

__all__ = [
    "MODEL_INPUT_BUILDER",
    "LEGACY_MODEL_INPUT_VERSION",
    "MODEL_INPUT_FALLBACK_VERSION",
    "MODEL_INPUT_HASH_POLICY",
    "MODEL_INPUT_TEXT_COLUMN",
    "MODEL_INPUT_VERSION",
    "build_model_input_text",
    "canonicalize_text",
    "parse_raw_http",
    "prepare_model_input",
    "prepare_model_input_for_version",
    "prepare_legacy_model_input",
    "preprocess_http_request",
    "redact_query_string",
    "redact_sensitive_text",
    "sanitize_model_input_request",
]
