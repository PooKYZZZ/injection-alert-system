from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

NotificationChannel = Literal["email", "telegram"]


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient: str
    subject: str
    text: str
    html: str
    idempotency_key: str

    def __post_init__(self) -> None:
        if not self.recipient or "@" not in self.recipient:
            raise ValueError("A valid recipient is required.")
        if not self.subject or not self.text or not self.html:
            raise ValueError("Email content is required.")
        if not 1 <= len(self.idempotency_key) <= 256:
            raise ValueError("The provider idempotency key is invalid.")


@dataclass(frozen=True, slots=True)
class ProviderSendResult:
    message_id: str


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    chat_id: str
    text: str

    def __post_init__(self) -> None:
        if not self.chat_id.strip():
            raise ValueError("A Telegram chat id is required.")
        if not 1 <= len(self.text) <= 4096:
            raise ValueError("Telegram message text is invalid.")


@dataclass(frozen=True, slots=True)
class OutboxJob:
    id: str
    kind: str
    recipient: str
    safe_payload: Mapping[str, object]
    template_version: int
    dedupe_key: str | None
    provider_idempotency_key: str
    attempt_count: int
    max_attempts: int
    deliver_before: datetime | None = None
    channel: NotificationChannel = "email"


@dataclass(frozen=True, slots=True)
class PendingNotification:
    kind: str
    recipient: str
    safe_payload: Mapping[str, object]
    template_version: int
    dedupe_key: str
    provider_idempotency_key: str
    deliver_before: datetime | None = None
    channel: NotificationChannel = "email"


@dataclass(frozen=True, slots=True)
class WorkerRunResult:
    claimed: int
    sent: int
    failed: int
    ambiguous: int = 0
