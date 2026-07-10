from __future__ import annotations

from html import escape
from typing import Mapping

from web_app.notifications.models import EmailMessage


class TemplatePayloadError(ValueError):
    pass


_THREAT_FIELDS = {
    "event_id",
    "timestamp",
    "attack_category",
    "confidence_tier",
    "action_taken",
    "route_path",
    "dashboard_url",
}


def _exact_strings(payload: Mapping[str, object], fields: set[str]) -> dict[str, str]:
    if set(payload) != fields:
        raise TemplatePayloadError("Template payload fields are invalid.")
    values: dict[str, str] = {}
    for field in fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value or len(value) > 2_000:
            raise TemplatePayloadError("Template payload value is invalid.")
        values[field] = value
    return values


def _paragraphs(lines: list[str]) -> str:
    return "".join(f"<p>{escape(line)}</p>" for line in lines)


def _render_threat(payload: Mapping[str, object]) -> tuple[str, str, str]:
    values = _exact_strings(payload, _THREAT_FIELDS)
    if "?" in values["route_path"] or "#" in values["route_path"]:
        raise TemplatePayloadError("Threat route must not include query or fragment data.")
    if not values["route_path"].startswith("/"):
        raise TemplatePayloadError("Threat route is invalid.")
    if not values["dashboard_url"].startswith(("https://", "http://localhost")):
        raise TemplatePayloadError("Dashboard URL is invalid.")
    subject = f"CyberTrace threat alert: {values['confidence_tier']}"
    lines = [
        "CyberTrace detected a security event.",
        f"Alert ID: {values['event_id']}",
        f"Timestamp: {values['timestamp']}",
        f"Category: {values['attack_category']}",
        f"Confidence: {values['confidence_tier']}",
        f"Action: {values['action_taken']}",
        f"Route: {values['route_path']}",
        f"Review: {values['dashboard_url']}",
    ]
    return subject, "\n".join(lines), _paragraphs(lines)


def _render_simple(
    kind: str, payload: Mapping[str, object]
) -> tuple[str, str, str]:
    specs: dict[str, tuple[str, str, str]] = {
        "password_setup": ("Set up your CyberTrace password", "setup_url", "Open this one-time setup link:"),
        "password_reset": ("Reset your CyberTrace password", "reset_url", "Open this one-time reset link:"),
        "email_verification": ("Verify your CyberTrace email", "verification_url", "Open this verification link:"),
        "email_recovery_otp": ("CyberTrace recovery code", "otp", "Your short-lived recovery code is:"),
    }
    notices: dict[str, tuple[str, str]] = {
        "password_changed": ("CyberTrace password changed", "Your CyberTrace password was changed."),
        "totp_enrolled": ("CyberTrace authenticator enrolled", "A TOTP authenticator was enrolled."),
        "totp_replaced": ("CyberTrace authenticator replaced", "Your TOTP authenticator was replaced."),
        "backup_code_used": ("CyberTrace backup code used", "A backup code was used for account recovery."),
        "admin_mfa_reset": ("CyberTrace MFA reset", "An administrator reset MFA for your account."),
        "account_disabled": ("CyberTrace account disabled", "Your CyberTrace account was disabled."),
        "account_reenabled": ("CyberTrace account re-enabled", "Your CyberTrace account was re-enabled."),
        "managed_email_changed": ("CyberTrace email changed", "Your CyberTrace account email address was changed."),
    }
    if kind in specs:
        subject, field, prefix = specs[kind]
        values = _exact_strings(payload, {field})
        lines = [prefix, values[field]]
        return subject, "\n".join(lines), _paragraphs(lines)
    if kind in notices:
        if payload:
            raise TemplatePayloadError("Template payload fields are invalid.")
        subject, notice = notices[kind]
        return subject, notice, _paragraphs([notice])
    raise TemplatePayloadError("Unknown notification template.")


def render_email(
    *,
    kind: str,
    recipient: str,
    payload: Mapping[str, object],
    template_version: int,
    idempotency_key: str,
) -> EmailMessage:
    if template_version != 1:
        raise TemplatePayloadError("Unsupported notification template version.")
    if kind == "threat_detected":
        subject, text, html = _render_threat(payload)
    else:
        subject, text, html = _render_simple(kind, payload)
    return EmailMessage(
        recipient=recipient,
        subject=subject,
        text=text,
        html=html,
        idempotency_key=idempotency_key,
    )
