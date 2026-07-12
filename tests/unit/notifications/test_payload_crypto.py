from __future__ import annotations

from base64 import b64encode

import pytest

from web_app.notifications.payload_crypto import (
    NotificationPayloadError,
    decrypt_notification_payload,
    encrypt_notification_payload,
)

CONTEXT = {
    "kind": "password_reset",
    "recipient": "owner@example.test",
    "idempotency_key": "password-reset/test-event",
}


@pytest.fixture(autouse=True)
def payload_key(monkeypatch):
    monkeypatch.setenv(
        "NOTIFICATION_PAYLOAD_ENCRYPTION_KEY",
        b64encode(bytes([7]) * 32).decode("ascii"),
    )


def test_payload_encryption_round_trips_with_unique_nonce() -> None:
    payload = {"reset_url": "https://example.test/reset?token=opaque"}

    first = encrypt_notification_payload(payload=payload, **CONTEXT)
    second = encrypt_notification_payload(payload=payload, **CONTEXT)

    assert first != second
    assert first["key_version"] == 1
    assert decrypt_notification_payload(envelope=first, **CONTEXT) == payload


@pytest.mark.parametrize("failure", ["tamper", "context", "key", "version"])
def test_payload_decryption_fails_closed(monkeypatch, failure: str) -> None:
    envelope = encrypt_notification_payload(payload={"otp": "123456"}, **CONTEXT)
    call_context = dict(CONTEXT)
    if failure == "tamper":
        ciphertext = str(envelope["ciphertext"])
        replacement = "A" if ciphertext[-1] != "A" else "B"
        envelope["ciphertext"] = f"{ciphertext[:-1]}{replacement}"
    elif failure == "context":
        call_context["idempotency_key"] = "different"
    elif failure == "key":
        monkeypatch.setenv(
            "NOTIFICATION_PAYLOAD_ENCRYPTION_KEY",
            b64encode(bytes([8]) * 32).decode("ascii"),
        )
    else:
        envelope["key_version"] = 99

    with pytest.raises(NotificationPayloadError, match="unavailable"):
        decrypt_notification_payload(envelope=envelope, **call_context)


def test_payload_encryption_fails_when_key_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("NOTIFICATION_PAYLOAD_ENCRYPTION_KEY")

    with pytest.raises(NotificationPayloadError, match="unavailable"):
        encrypt_notification_payload(payload={"otp": "123456"}, **CONTEXT)


def test_payload_contract_matches_frontend_aes_gcm_vector() -> None:
    payload = decrypt_notification_payload(
        kind="password_reset",
        recipient="owner@example.test",
        idempotency_key="password-reset/interoperability",
        envelope={
            "nonce": "AAECAwQFBgcICQoL",
            "ciphertext": (
                "Y6ObFW5srRYCwIm-2HoEjpVMxbQ3TRJJd6MT1uv5GWCtG2mQ8rxUicuRrN05"
                "mYhamkQ5C7ulgeQQLdjpgr3cAZPJ6BuUnuHpQ4VXEwYD"
            ),
            "key_version": 1,
        },
    )

    assert payload == {
        "reset_url": "https://example.test/reset?token=interoperable"
    }
