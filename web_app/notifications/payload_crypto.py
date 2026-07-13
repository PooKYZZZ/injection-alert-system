from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Mapping
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AAD_PREFIX: Final = "cybertrace:notification-payload:v1"
KEY_VERSION: Final = 1
NONCE_BYTES: Final = 12
MAX_CONTEXT_LENGTH: Final = 320
MAX_PAYLOAD_FIELDS: Final = 16
MAX_PAYLOAD_VALUE_LENGTH: Final = 4_096
PROTECTED_NOTIFICATION_KINDS: Final = frozenset(
    {
        "password_setup",
        "password_reset",
        "email_verification",
        "email_recovery_otp",
    }
)
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class NotificationPayloadError(RuntimeError):
    pass


def _unavailable() -> NotificationPayloadError:
    return NotificationPayloadError("Notification payload is unavailable.")


def _encryption_key() -> bytes:
    raw = os.getenv("NOTIFICATION_PAYLOAD_ENCRYPTION_KEY", "").strip()
    if not raw:
        raise _unavailable()
    try:
        key = (
            bytes.fromhex(raw)
            if re.fullmatch(r"[0-9a-fA-F]{64}", raw)
            else base64.b64decode(raw, validate=True)
        )
    except (ValueError, base64.binascii.Error) as exc:
        raise _unavailable() from exc
    if len(key) != 32:
        raise _unavailable()
    return key


def _context_aad(*, kind: str, recipient: str, idempotency_key: str) -> bytes:
    values = (kind, recipient, idempotency_key)
    if any(
        not isinstance(value, str)
        or not 1 <= len(value) <= MAX_CONTEXT_LENGTH
        or "\0" in value
        for value in values
    ):
        raise _unavailable()
    return "\0".join((AAD_PREFIX, *values)).encode("utf-8")


def _payload(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise _unavailable()
    items = list(value.items())
    if not 1 <= len(items) <= MAX_PAYLOAD_FIELDS:
        raise _unavailable()
    payload: dict[str, str] = {}
    for key, item in items:
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 128
            or not isinstance(item, str)
            or not 1 <= len(item) <= MAX_PAYLOAD_VALUE_LENGTH
        ):
            raise _unavailable()
        payload[key] = item
    return payload


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: object) -> bytes:
    if not isinstance(value, str) or _BASE64URL.fullmatch(value) is None:
        raise _unavailable()
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise _unavailable() from exc
    if _encode(decoded) != value:
        raise _unavailable()
    return decoded


def encrypt_notification_payload(
    *,
    kind: str,
    recipient: str,
    idempotency_key: str,
    payload: Mapping[str, str],
) -> dict[str, object]:
    try:
        nonce = os.urandom(NONCE_BYTES)
        plaintext = json.dumps(
            _payload(payload), separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        ciphertext = AESGCM(_encryption_key()).encrypt(
            nonce,
            plaintext,
            _context_aad(
                kind=kind,
                recipient=recipient,
                idempotency_key=idempotency_key,
            ),
        )
        return {
            "ciphertext": _encode(ciphertext),
            "nonce": _encode(nonce),
            "key_version": KEY_VERSION,
        }
    except NotificationPayloadError:
        raise
    except Exception as exc:
        raise _unavailable() from exc


def decrypt_notification_payload(
    *,
    kind: str,
    recipient: str,
    idempotency_key: str,
    envelope: Mapping[str, object],
) -> dict[str, str]:
    try:
        if set(envelope) != {"ciphertext", "nonce", "key_version"}:
            raise _unavailable()
        if envelope.get("key_version") != KEY_VERSION:
            raise _unavailable()
        plaintext = AESGCM(_encryption_key()).decrypt(
            _decode(envelope.get("nonce")),
            _decode(envelope.get("ciphertext")),
            _context_aad(
                kind=kind,
                recipient=recipient,
                idempotency_key=idempotency_key,
            ),
        )
        return _payload(json.loads(plaintext.decode("utf-8")))
    except NotificationPayloadError:
        raise
    except Exception as exc:
        raise _unavailable() from exc
