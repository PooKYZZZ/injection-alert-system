from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from web_app.notifications.models import EmailMessage, ProviderSendResult
from web_app.notifications.providers import EmailProvider, ResendEmailProvider
from web_app.notifications.providers import EmailProviderError

APPROVED_SMOKE_RECIPIENT = "froilangayaom@gmail.com"


class SmokeSettings(Protocol):
    resend_live_test_enabled: bool
    resend_api_key: str | None
    resend_from_email: str
    resend_smoke_test_to: str | None


class LiveSmokeDisabled(RuntimeError):
    pass


class LiveSmokeConfigurationError(RuntimeError):
    pass


async def run_live_smoke(
    settings: SmokeSettings,
    *,
    provider: EmailProvider | None = None,
) -> ProviderSendResult:
    if not settings.resend_live_test_enabled:
        raise LiveSmokeDisabled("Live Resend smoke testing is disabled.")
    if not settings.resend_api_key or not settings.resend_from_email:
        raise LiveSmokeConfigurationError("Live Resend configuration is incomplete.")
    if settings.resend_smoke_test_to != APPROVED_SMOKE_RECIPIENT:
        raise LiveSmokeConfigurationError("Live Resend recipient is not approved.")
    active_provider = provider or ResendEmailProvider(
        api_key=settings.resend_api_key,
        from_email=settings.resend_from_email,
    )
    text = "This is a development-only provider connectivity test."
    return await active_provider.send(
        EmailMessage(
            recipient=APPROVED_SMOKE_RECIPIENT,
            subject="CyberTrace Resend smoke test",
            text=text,
            html=f"<p>{text}</p>",
            idempotency_key=f"development-smoke/{uuid4()}",
        )
    )


async def run_smoke_cli(
    settings: SmokeSettings,
    *,
    provider: EmailProvider | None = None,
) -> int:
    try:
        result = await run_live_smoke(settings, provider=provider)
    except LiveSmokeDisabled:
        print("SKIP: live Resend smoke test is disabled")
        return 2
    except LiveSmokeConfigurationError:
        print("FAIL: live Resend smoke configuration is invalid")
        return 1
    except EmailProviderError as exc:
        print(f"FAIL: Resend provider rejected the smoke test ({exc.error_class})")
        return 1
    print(f"PASS: Resend accepted the smoke test ({result.message_id})")
    return 0
