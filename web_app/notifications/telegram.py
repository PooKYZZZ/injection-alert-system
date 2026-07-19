from __future__ import annotations

from typing import Mapping

import httpx

from web_app.notifications.models import ProviderSendResult, TelegramMessage
from web_app.notifications.providers import NotificationProviderError

_FIELDS = {
    "event_id",
    "timestamp",
    "attack_category",
    "confidence_tier",
    "confidence",
    "request_method",
    "route_path",
    "dashboard_url",
}


class TelegramPayloadError(ValueError):
    pass


def render_telegram_threat(
    chat_id: str,
    payload: Mapping[str, object],
    template_version: int,
) -> TelegramMessage:
    if template_version != 1 or set(payload) != _FIELDS:
        raise TelegramPayloadError("Telegram threat payload is invalid.")
    strings: dict[str, str] = {}
    for field in _FIELDS - {"confidence"}:
        value = payload.get(field)
        if not isinstance(value, str) or not value or len(value) > 2_000:
            raise TelegramPayloadError("Telegram threat payload is invalid.")
        strings[field] = value
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise TelegramPayloadError("Telegram confidence is invalid.")
    if not 0 <= float(confidence) <= 1:
        raise TelegramPayloadError("Telegram confidence is invalid.")
    if strings["confidence_tier"] not in {"HIGH", "CRITICAL"}:
        raise TelegramPayloadError("Telegram confidence tier is invalid.")
    if "?" in strings["route_path"] or "#" in strings["route_path"]:
        raise TelegramPayloadError("Telegram route is invalid.")
    if not strings["route_path"].startswith("/"):
        raise TelegramPayloadError("Telegram route is invalid.")
    if not strings["dashboard_url"].startswith(("https://", "http://localhost")):
        raise TelegramPayloadError("Telegram dashboard URL is invalid.")
    icon = "🚨" if strings["confidence_tier"] == "CRITICAL" else "⚠️"
    text = "\n".join(
        [
            f"{icon} CYBERTRACE — {strings['confidence_tier']}-CONFIDENCE THREAT",
            "",
            f"Alert ID: {strings['event_id']}",
            f"Time: {strings['timestamp']}",
            f"Attack: {strings['attack_category']}",
            f"Confidence tier: {strings['confidence_tier']}",
            f"Confidence: {float(confidence) * 100:.1f}%",
            f"Request: {strings['request_method']} {strings['route_path']}",
            "",
            "Review:",
            strings["dashboard_url"],
        ]
    )
    return TelegramMessage(chat_id=chat_id, text=text)


class TelegramProvider:
    def __init__(
        self,
        *,
        bot_token: str,
        client: httpx.AsyncClient | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        if not bot_token.strip():
            raise ValueError("Telegram provider configuration is incomplete.")
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=10.0, write=10.0, pool=2.0
        )
        self._client = client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = client is None

    async def send(self, message: TelegramMessage) -> ProviderSendResult:
        try:
            response = await self._client.post(
                self._url,
                json={
                    "chat_id": message.chat_id,
                    "text": message.text,
                    "link_preview_options": {"is_disabled": True},
                },
                timeout=self._timeout,
            )
        except (httpx.ConnectTimeout, httpx.PoolTimeout, httpx.ConnectError) as exc:
            raise NotificationProviderError(
                "telegram_connect_failed", retryable=True
            ) from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise NotificationProviderError(
                "telegram_delivery_ambiguous",
                retryable=False,
                delivery_ambiguous=True,
            ) from exc
        except httpx.TransportError as exc:
            raise NotificationProviderError(
                "telegram_transport_failed", retryable=True
            ) from exc

        if response.status_code == 429:
            raise NotificationProviderError(
                "telegram_rate_limited",
                retryable=True,
                retry_after_seconds=self._retry_after(response),
            )
        if not 200 <= response.status_code < 300:
            mapping = {
                400: "telegram_request_invalid",
                401: "telegram_auth_failed",
                403: "telegram_destination_invalid",
            }
            raise NotificationProviderError(
                mapping.get(response.status_code, "telegram_server_error"),
                retryable=response.status_code >= 500,
            )
        try:
            body = response.json()
            message_id = body["result"]["message_id"]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise NotificationProviderError(
                "telegram_malformed_response",
                retryable=False,
                delivery_ambiguous=True,
            ) from exc
        if not isinstance(message_id, int) or isinstance(message_id, bool):
            raise NotificationProviderError(
                "telegram_malformed_response",
                retryable=False,
                delivery_ambiguous=True,
            )
        return ProviderSendResult(message_id=str(message_id))

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _retry_after(response: httpx.Response) -> int:
        try:
            value = response.json().get("parameters", {}).get("retry_after")
        except (ValueError, AttributeError):
            value = None
        if not isinstance(value, int) or isinstance(value, bool):
            return 30
        return min(3_600, max(0, value))
