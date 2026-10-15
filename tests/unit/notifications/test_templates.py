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
            "dashboard_url": "https://dashboard.example.test/traffic-history?alert_id=42",
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
        "dashboard_url": "https://dashboard.example.test/traffic-history?alert_id=42",
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

    assert message.subject == "CyberTrace Email Changed"
    assert "email address was changed" in message.text


def test_email_recovery_completion_notice_is_supported_without_secret_payload() -> None:
    message = render_email(
        kind="email_recovery_completed",
        recipient="owner@example.test",
        payload={},
        template_version=1,
        idempotency_key="email-recovery-completed/event-1",
    )

    assert message.subject == "CyberTrace Account Recovery Completed"
    assert "recovery was completed" in message.text


def test_requested_security_templates_share_layout_and_plain_text_fallback() -> None:
    cases = [
        (
            "totp_enrolled",
            {},
            "CyberTrace Authenticator Enrolled",
            "Future sign-ins may require",
        ),
        (
            "email_recovery_completed",
            {},
            "CyberTrace Account Recovery Completed",
            "Review your security settings",
        ),
        (
            "email_recovery_otp",
            {"otp": "123456"},
            "CyberTrace Recovery Code",
            "expires in 5 minutes",
        ),
        (
            "password_changed",
            {},
            "CyberTrace Password Changed",
            "No action is needed",
        ),
        (
            "password_reset",
            {"reset_url": "https://app.example.test/reset-password?token=opaque"},
            "Reset Your CyberTrace Password",
            "expires in 30 minutes",
        ),
    ]

    for index, (kind, payload, subject, expected_text) in enumerate(cases):
        message = render_email(
            kind=kind,
            recipient="owner@example.test",
            payload=payload,
            template_version=1,
            idempotency_key=f"security/{index}",
        )

        assert message.subject == subject
        assert message.html.startswith("<!doctype html>")
        assert "CyberTrace" in message.html
        assert expected_text in message.text


def test_password_reset_keeps_the_same_action_url_in_both_representations() -> None:
    url = "https://app.example.test/reset-password?token=opaque&amp=1"
    message = render_email(
        kind="password_reset",
        recipient="owner@example.test",
        payload={"reset_url": url},
        template_version=1,
        idempotency_key="password-reset/1",
    )

    assert f"Reset password: {url}" in message.text
    assert "href=\"https://app.example.test/reset-password?token=opaque&amp;amp=1\"" in message.html
    assert "opaque" in message.text


def test_recovery_otp_does_not_accept_backup_code_or_session_payloads() -> None:
    with pytest.raises(TemplatePayloadError):
        render_email(
            kind="email_recovery_otp",
            recipient="owner@example.test",
            payload={"otp": "123456", "backup_code": "reusable-code"},
            template_version=1,
            idempotency_key="recovery/1",
        )

    message = render_email(
        kind="email_recovery_otp",
        recipient="owner@example.test",
        payload={"otp": "123456"},
        template_version=1,
        idempotency_key="recovery/2",
    )
    assert "reusable-code" not in message.text
    assert "session" not in message.text.lower()
