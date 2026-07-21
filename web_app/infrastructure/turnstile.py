from __future__ import annotations

import httpx

from web_app.domain.enforcement import TurnstileVerificationResult

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_ACTION = "record_search_enforcement"
TURNSTILE_TEST_SECRETS = {
    "1x0000000000000000000000000000000AA",
    "2x0000000000000000000000000000000AA",
    "3x0000000000000000000000000000000AA",
}
TURNSTILE_UNAVAILABLE_ERROR_CODES = {
    "internal-error",
    "invalid-input-secret",
    "missing-input-secret",
    "bad-request",
}


class TurnstileVerifier:
    """Server-only Cloudflare Siteverify adapter for enforcement challenges."""

    def __init__(
        self,
        *,
        secret_key: str,
        expected_hostname: str,
        timeout_seconds: float = 3.0,
        test_mode: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._secret_key = secret_key.strip()
        self._expected_hostname = expected_hostname.strip()
        self._timeout = httpx.Timeout(timeout_seconds)
        self._test_mode = test_mode and self._secret_key in TURNSTILE_TEST_SECRETS
        self._client = client

    async def verify(
        self, *, token: str, remote_ip: str
    ) -> TurnstileVerificationResult:
        if (
            not self._secret_key
            or not self._expected_hostname
            or not isinstance(token, str)
            or not 1 <= len(token) <= 2048
        ):
            return TurnstileVerificationResult(success=False)

        close_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                SITEVERIFY_URL,
                data={
                    "secret": self._secret_key,
                    "response": token,
                    "remoteip": remote_ip,
                },
            )
            if response.status_code < 200 or response.status_code >= 300:
                return TurnstileVerificationResult(success=False, unavailable=True)
            try:
                payload = response.json()
            except ValueError:
                return TurnstileVerificationResult(success=False, unavailable=True)
            if not isinstance(payload, dict):
                return TurnstileVerificationResult(success=False, unavailable=True)
            error_codes = payload.get("error-codes", [])
            if (
                payload.get("success") is not True
                and isinstance(error_codes, list)
                and any(
                    code in TURNSTILE_UNAVAILABLE_ERROR_CODES
                    for code in error_codes
                )
            ):
                return TurnstileVerificationResult(success=False, unavailable=True)
            if self._test_mode and payload.get("success") is True:
                return TurnstileVerificationResult(success=True)
            success = (
                payload.get("success") is True
                and payload.get("action") == TURNSTILE_ACTION
                and payload.get("hostname") == self._expected_hostname
            )
            return TurnstileVerificationResult(success=success)
        except httpx.TimeoutException, httpx.TransportError:
            return TurnstileVerificationResult(success=False, unavailable=True)
        finally:
            if close_client:
                await client.aclose()
