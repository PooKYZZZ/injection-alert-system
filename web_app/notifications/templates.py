from __future__ import annotations

from html import escape
from typing import Mapping
from urllib.parse import urlsplit

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


def _trusted_action_url(value: str) -> str:
    if (
        not value
        or len(value) > 2_000
        or any(character in value for character in "\r\n")
    ):
        raise TemplatePayloadError("Action URL is invalid.")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise TemplatePayloadError("Action URL is invalid.") from exc
    if parsed.scheme == "https" and parsed.netloc:
        return value
    if parsed.scheme == "http" and parsed.hostname == "localhost":
        return value
    raise TemplatePayloadError("Action URL is invalid.")


def _render_layout(
    *,
    title: str,
    lines: list[str],
    security_notice: str,
    action: tuple[str, str] | None = None,
) -> tuple[str, str]:
    text_lines = ["CyberTrace", title, "", *lines]
    if action is not None:
        text_lines.extend(["", f"{action[0]}: {action[1]}"])
    text_lines.extend(
        [
            "",
            f"Security notice: {security_notice}",
            "",
            "This is an automated CyberTrace security message.",
        ]
    )

    html_action = ""
    if action is not None:
        label, url = action
        escaped_url = escape(url, quote=True)
        html_action = (
            '<p style="margin:24px 0;text-align:center;">'
            f'<a href="{escaped_url}" '
            'style="background:#c77e32;border-radius:6px;color:#ffffff;'
            'display:inline-block;font-weight:700;padding:12px 18px;'
            'text-decoration:none;">'
            f"{escape(label)}"
            "</a></p>"
            f'<p class="cybertrace-action-url" style="color:#475569;font-size:14px;line-height:1.6;">'
            f"{escape(label)} URL: {escaped_url}</p>"
        )

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark">
    <style>
      @media (prefers-color-scheme: dark) {{
        body {{ background:#111827 !important;color:#e5e7eb !important; }}
        .cybertrace-card {{ background:#1f2937 !important;border-color:#374151 !important; }}
        .cybertrace-header {{ background:#0f172a !important; }}
        .cybertrace-title {{ color:#f8fafc !important; }}
        .cybertrace-action-url {{ color:#cbd5e1 !important; }}
        .cybertrace-security {{ background:#3b3020 !important;border-color:#d39a52 !important; }}
        .cybertrace-footer {{ border-color:#374151 !important;color:#94a3b8 !important; }}
      }}
    </style>
  </head>
  <body style="background:#f3f5f7;color:#24313d;font-family:Arial,Helvetica,sans-serif;margin:0;padding:24px;">
    <div class="cybertrace-card" style="background:#ffffff;border:1px solid #d7dee5;border-radius:8px;margin:0 auto;max-width:600px;overflow:hidden;">
      <header class="cybertrace-header" style="background:#1d2a38;color:#ffffff;padding:20px 24px;">
        <div style="font-size:18px;font-weight:700;letter-spacing:.02em;">CyberTrace</div>
      </header>
      <main style="padding:28px 24px;">
        <h1 class="cybertrace-title" style="color:#15202b;font-size:24px;line-height:1.25;margin:0 0 18px;">{escape(title)}</h1>
        {_paragraphs(lines)}
        {html_action}
        <div class="cybertrace-security" role="note" style="background:#f7f4ec;border-left:4px solid #c77e32;margin-top:24px;padding:12px 16px;">
          <strong>Security notice</strong>
          <p style="margin:8px 0 0;">{escape(security_notice)}</p>
        </div>
      </main>
      <footer class="cybertrace-footer" style="border-top:1px solid #d7dee5;color:#64748b;font-size:13px;line-height:1.5;padding:16px 24px;">
        This is an automated CyberTrace security message.
      </footer>
    </div>
  </body>
</html>"""
    return "\n".join(text_lines), html


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


def _render_security_email(
    kind: str, payload: Mapping[str, object]
) -> tuple[str, str, str]:
    action_specs: dict[str, tuple[str, str, str]] = {
        "password_setup": (
            "Set up your CyberTrace password",
            "setup_url",
            "Open this one-time setup link:",
        ),
        "email_verification": (
            "Verify your CyberTrace email",
            "verification_url",
            "Open this verification link:",
        ),
    }
    if kind in action_specs:
        subject, field, prefix = action_specs[kind]
        values = _exact_strings(payload, {field})
        url = _trusted_action_url(values[field])
        text, html = _render_layout(
            title=subject,
            lines=[prefix],
            security_notice="Use this link only for the requested account action.",
            action=("Open link", url),
        )
        return subject, text, html

    if kind == "password_reset":
        values = _exact_strings(payload, {"reset_url"})
        reset_url = _trusted_action_url(values["reset_url"])
        subject = "Reset Your CyberTrace Password"
        text, html = _render_layout(
            title=subject,
            lines=[
                "We received a request to reset your CyberTrace password.",
                "If you made this request, use the action below to choose a new password.",
            ],
            security_notice=(
                "This link expires in 30 minutes. A newer reset request invalidates an "
                "older link. Ignore this message if you did not request a reset."
            ),
            action=("Reset password", reset_url),
        )
        return subject, text, html

    if kind == "email_recovery_otp":
        values = _exact_strings(payload, {"otp"})
        subject = "CyberTrace Recovery Code"
        text, html = _render_layout(
            title=subject,
            lines=[
                "Use this short-lived email recovery code to complete the account recovery step:",
                values["otp"],
            ],
            security_notice=(
                "This email OTP expires in 5 minutes, works once, and must never be shared. "
                "CyberTrace staff will never ask you to disclose it. It is not a reusable MFA backup code."
            ),
        )
        return subject, text, html

    notices: dict[str, tuple[str, list[str], str]] = {
        "password_changed": (
            "CyberTrace Password Changed",
            [
                "Your CyberTrace password was changed.",
                "No action is needed if you made this change.",
                "If you did not make this change, use the CyberTrace password recovery flow or contact your security administrator.",
            ],
            "Never share your password. CyberTrace will not include it in this message.",
        ),
        "totp_enrolled": (
            "CyberTrace Authenticator Enrolled",
            [
                "An authenticator was enrolled for your CyberTrace account.",
                "Future sign-ins may require verification in your authenticator app.",
                "Store your backup codes in a password manager or secure offline location.",
                "If you did not enroll this authenticator, review your account security and contact your administrator.",
            ],
            "Authenticator setup secrets and backup-code values are never included in this email.",
        ),
        "totp_replaced": (
            "CyberTrace Authenticator Replaced",
            [
                "Your CyberTrace authenticator was replaced.",
                "If you did not make this change, review your account security and contact your administrator.",
            ],
            "Authenticator setup secrets and backup-code values are never included in this email.",
        ),
        "backup_code_used": (
            "CyberTrace Backup Code Used",
            [
                "A backup code was used for CyberTrace account recovery.",
                "If you did not make this change, review your account security and generate new recovery material if required.",
            ],
            "Reusable backup-code values are never included in this email.",
        ),
        "admin_mfa_reset": (
            "CyberTrace MFA Reset",
            [
                "An administrator reset MFA for your CyberTrace account.",
                "You must enroll a new authenticator before protected sign-ins can continue.",
            ],
            "Authenticator setup secrets and backup-code values are never included in this email.",
        ),
        "account_disabled": (
            "CyberTrace Account Disabled",
            [
                "Your CyberTrace account was disabled.",
                "Contact your security administrator if you believe this was unexpected.",
            ],
            "This message does not contain credentials or session information.",
        ),
        "account_reenabled": (
            "CyberTrace Account Re-enabled",
            [
                "Your CyberTrace account was re-enabled.",
                "Contact your security administrator if you did not expect this change.",
            ],
            "This message does not contain credentials or session information.",
        ),
        "managed_email_changed": (
            "CyberTrace Email Changed",
            [
                "Your CyberTrace account email address was changed.",
                "Contact your security administrator if you did not expect this change.",
            ],
            "This message does not contain credentials or session information.",
        ),
        "email_recovery_completed": (
            "CyberTrace Account Recovery Completed",
            [
                "Your CyberTrace account recovery was completed.",
                "Review your security settings when you next sign in.",
                "If you did not complete this recovery, contact your security administrator immediately.",
            ],
            "Only the recovery event is confirmed here; no session or recovery token details are included.",
        ),
    }
    if kind in notices:
        if payload:
            raise TemplatePayloadError("Template payload fields are invalid.")
        subject, lines, security_notice = notices[kind]
        text, html = _render_layout(
            title=subject,
            lines=lines,
            security_notice=security_notice,
        )
        return subject, text, html
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
        subject, text, html = _render_security_email(kind, payload)
    return EmailMessage(
        recipient=recipient,
        subject=subject,
        text=text,
        html=html,
        idempotency_key=idempotency_key,
    )
