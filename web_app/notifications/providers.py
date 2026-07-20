from __future__ import annotations

import re
from typing import Protocol

import httpx

from web_app.notifications.models import EmailMessage, ProviderSendResult

_SAFE_ERROR_CLASS = re.compile(r"^[a-z0-9_]{1,64}$")
_SAFE_MESSAGE_ID = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> ProviderSendResult: ...

    async def close(self) -> None: ...


class NotificationProviderError(RuntimeError):
    def __init__(
        self,
        error_class: str,
        *,
        retryable: bool,
        retry_after_seconds: int | None = None,
        delivery_ambiguous: bool = False,
    ) -> None:
        safe_class = (
            error_class if _SAFE_ERROR_CLASS.fullmatch(error_class) else "provider_error"
        )
        super().__init__(safe_class)
        self.error_class = safe_class
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.delivery_ambiguous = delivery_ambiguous


class EmailProviderError(NotificationProviderError):
    pass


class FakeEmailProvider:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> ProviderSendResult:
        self.messages.append(message)
        return ProviderSendResult(message_id=f"fake-{len(self.messages)}")

    async def close(self) -> None:
        return None


class ResendEmailProvider:
    _API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_key or not from_email:
            raise ValueError("Resend provider configuration is incomplete.")
        self._api_key = api_key
        self._from_email = from_email
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None
        self._timeout = timeout_seconds

    async def send(self, message: EmailMessage) -> ProviderSendResult:
        return await self._send(self._client, message)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _send(
        self, client: httpx.AsyncClient, message: EmailMessage
    ) -> ProviderSendResult:
        try:
            response = await client.post(
                self._API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": message.idempotency_key,
                    "Content-Type": "application/json",
                },
                json={
                    "from": self._from_email,
                    "to": [message.recipient],
                    "subject": message.subject,
                    "text": message.text,
                    "html": message.html,
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise EmailProviderError("provider_timeout", retryable=True) from exc
        except httpx.TransportError as exc:
            raise EmailProviderError("provider_transport", retryable=True) from exc

        if not 200 <= response.status_code < 300:
            error_class = self._read_error_class(response)
            retryable = response.status_code in {408, 425, 429} or response.status_code >= 500
            if response.status_code == 409:
                retryable = error_class == "concurrent_idempotent_requests"
            raise EmailProviderError(error_class, retryable=retryable)

        try:
            message_id = response.json().get("id")
        except (ValueError, AttributeError) as exc:
            raise EmailProviderError("provider_malformed_response", retryable=False) from exc
        if not isinstance(message_id, str) or not _SAFE_MESSAGE_ID.fullmatch(
            message_id
        ):
            raise EmailProviderError("provider_malformed_response", retryable=False)
        return ProviderSendResult(message_id=message_id)

    @staticmethod
    def _read_error_class(response: httpx.Response) -> str:
        try:
            value = response.json().get("name")
        except (ValueError, AttributeError):
            value = None
        if isinstance(value, str) and _SAFE_ERROR_CLASS.fullmatch(value):
            return value
        return f"provider_http_{response.status_code}"
