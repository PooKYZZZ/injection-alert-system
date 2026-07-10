from __future__ import annotations

import pytest

from web_app.notifications.templates import TemplatePayloadError, render_email


def test_threat_template_allows_only_safe_fields_and_escapes_html() -> None:
    message = render_email(
        kind="threat_detected",
        recipient="soc@example.test",
        payload={
            "event_id": "alert-42",
            "timestamp": "2026-07-10T09:00:00Z",
            "attack_category": "SQL Injection <script>",
            "confidence_tier": "CRITICAL",
            "action_taken": "BLOCKED",
            "route_path": "/records/<script>",
            "dashboard_url": "https://dashboard.example.test/alerts/42",
        },
        template_version=1,
        idempotency_key="threat/alert-42",
    )

    assert message.subject == "CyberTrace threat alert: CRITICAL"
    assert "<script>" not in message.html
    assert "&lt;script&gt;" in message.html
    assert "SQL Injection <script>" in message.text
    assert "raw request" not in message.text.lower()


def test_threat_template_rejects_query_strings_and_unknown_payload_fields() -> None:
    base = {
        "event_id": "alert-42",
        "timestamp": "2026-07-10T09:00:00Z",
        "attack_category": "SQL Injection",
        "confidence_tier": "HIGH",
        "action_taken": "BLOCKED",
        "route_path": "/records/search?password=secret",
        "dashboard_url": "https://dashboard.example.test/alerts/42",
        "query_string": "password=secret",
    }

    with pytest.raises(TemplatePayloadError):
        render_email(
            kind="threat_detected",
            recipient="soc@example.test",
            payload=base,
            template_version=1,
            idempotency_key="threat/alert-42",
        )


def test_unknown_template_or_version_fails_closed() -> None:
    with pytest.raises(TemplatePayloadError):
        render_email(
            kind="unknown",
            recipient="soc@example.test",
            payload={},
            template_version=99,
            idempotency_key="unknown/1",
        )


def test_managed_email_change_owner_notification_is_supported() -> None:
    message = render_email(
        kind="managed_email_changed",
        recipient="old-address@example.test",
        payload={},
        template_version=1,
        idempotency_key="managed-email/account-1",
    )

    assert message.subject == "CyberTrace email changed"
    assert "email address was changed" in message.text
