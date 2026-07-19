from __future__ import annotations

from typing import Mapping, Protocol

from web_app.notifications.models import (
    EmailMessage,
    OutboxJob,
    ProviderSendResult,
    TelegramMessage,
)
from web_app.notifications.providers import NotificationProviderError
from web_app.notifications.telegram import render_telegram_threat
from web_app.notifications.templates import render_email


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> ProviderSendResult: ...
    async def close(self) -> None: ...


class TelegramSender(Protocol):
    async def send(self, message: TelegramMessage) -> ProviderSendResult: ...
    async def close(self) -> None: ...


class DeliveryRouter:
    def __init__(
        self,
        *,
        email_provider: EmailSender,
        telegram_provider: TelegramSender | None = None,
    ) -> None:
        self._email_provider = email_provider
        self._telegram_provider = telegram_provider

    async def deliver(
        self, job: OutboxJob, payload: Mapping[str, object]
    ) -> ProviderSendResult:
        if job.channel == "email":
            message = render_email(
                kind=job.kind,
                recipient=job.recipient,
                payload=payload,
                template_version=job.template_version,
                idempotency_key=job.provider_idempotency_key,
            )
            return await self._email_provider.send(message)
        if job.channel == "telegram":
            if self._telegram_provider is None:
                raise NotificationProviderError(
                    "telegram_unavailable", retryable=False
                )
            message = render_telegram_threat(
                job.recipient, payload, job.template_version
            )
            return await self._telegram_provider.send(message)
        raise NotificationProviderError("channel_unsupported", retryable=False)

    async def close(self) -> None:
        await self._email_provider.close()
        if self._telegram_provider is not None:
            await self._telegram_provider.close()
