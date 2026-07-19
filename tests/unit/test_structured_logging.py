import json
import logging

from web_app.observability.context import (
    reset_request_context,
    set_request_context,
)
from web_app.observability.structured_logging import log_event


def test_log_event_emits_parseable_json_with_stable_required_fields(
    caplog, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "testing")
    logger = logging.getLogger("tests.structured")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            "test.completed",
            "Test completed",
            status_code=200,
        )

    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["level"] == "INFO"
    assert payload["event"] == "test.completed"
    assert payload["message"] == "Test completed"
    assert payload["service"] == "cybertrace-api"
    assert payload["component"] == "fastapi"
    assert payload["environment"] == "testing"
    assert payload["status_code"] == 200
    assert payload["timestamp"].endswith("Z")
    assert isinstance(payload["timestamp"], str)


def test_log_event_includes_context_ids_and_redacts_nested_secrets(caplog):
    logger = logging.getLogger("tests.structured.context")
    tokens = set_request_context(
        request_id="request-123",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
    )
    try:
        with caplog.at_level(logging.WARNING, logger=logger.name):
            log_event(
                logger,
                "request.failed",
                "Request failed",
                level="WARNING",
                headers={"Authorization": "Bearer secret"},
                api_secret_key="top-secret",
            )
    finally:
        reset_request_context(tokens)

    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["request_id"] == "request-123"
    assert payload["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert payload["span_id"] == "00f067aa0ba902b7"
    assert payload["headers"]["Authorization"] == "[REDACTED]"
    assert payload["api_secret_key"] == "[REDACTED]"
    assert "top-secret" not in caplog.records[-1].getMessage()


def test_log_event_redacts_telegram_bot_token(caplog):
    logger = logging.getLogger("tests.structured.telegram")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            "notification.telegram_unavailable",
            "Telegram unavailable",
            TELEGRAM_BOT_TOKEN="telegram-secret",
        )

    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["TELEGRAM_BOT_TOKEN"] == "[REDACTED]"
    assert "telegram-secret" not in caplog.records[-1].getMessage()


def test_log_event_safely_serializes_unknown_values(caplog):
    class UnknownValue:
        def __str__(self):
            return "safe-object"

    logger = logging.getLogger("tests.structured.unknown")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            "test.unknown",
            "Unknown value",
            detail=UnknownValue(),
        )

    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["detail"] == "safe-object"


def test_log_event_never_raises_when_logger_fails():
    class BrokenLogger:
        def log(self, *_args, **_kwargs):
            raise RuntimeError("logging unavailable")

    log_event(BrokenLogger(), "test.failed", "Must not escape")


def test_log_event_normalizes_unknown_level_to_info(caplog):
    logger = logging.getLogger("tests.structured.invalid-level")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            "test.invalid_level",
            "Invalid level",
            level="BOGUS",
        )

    record = caplog.records[-1]
    payload = json.loads(record.getMessage())
    assert record.levelno == logging.INFO
    assert payload["level"] == "INFO"
    assert payload["level"] != "BOGUS"
