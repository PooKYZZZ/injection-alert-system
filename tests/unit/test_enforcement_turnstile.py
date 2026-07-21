import httpx
import pytest

from web_app.application.enforcement_use_cases import TurnstileVerificationResult
from web_app.infrastructure.turnstile import TurnstileVerifier


@pytest.mark.asyncio
async def test_turnstile_verifier_accepts_successful_expected_action_and_hostname():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/turnstile/v0/siteverify")
        body = request.content.decode()
        assert "response=token-value" in body
        return httpx.Response(
            200,
            json={
                "success": True,
                "action": "record_search_enforcement",
                "hostname": "localhost",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await TurnstileVerifier(
            secret_key="server-only-secret",
            expected_hostname="localhost",
            client=client,
        ).verify(token="token-value", remote_ip="203.0.113.10")

    assert result == TurnstileVerificationResult(success=True)


@pytest.mark.asyncio
async def test_turnstile_verifier_rejects_action_hostname_and_provider_failures():
    async def handler(request: httpx.Request) -> httpx.Response:
        if b"response=provider-token" in request.content:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"success": True, "action": "login", "hostname": "evil.example"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        invalid = await TurnstileVerifier(
            secret_key="secret",
            expected_hostname="localhost",
            client=client,
        ).verify(token="token", remote_ip="203.0.113.10")
        unavailable = await TurnstileVerifier(
            secret_key="secret",
            expected_hostname="localhost",
            client=client,
        ).verify(token="provider-token", remote_ip="203.0.113.10")

    assert invalid == TurnstileVerificationResult(success=False)
    assert unavailable == TurnstileVerificationResult(success=False, unavailable=True)


@pytest.mark.asyncio
async def test_turnstile_verifier_rejects_empty_or_oversized_tokens_without_provider_call():
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"success": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = TurnstileVerifier(
            secret_key="secret", expected_hostname="localhost", client=client
        )
        empty = await verifier.verify(token="", remote_ip="203.0.113.10")
        oversized = await verifier.verify(token="x" * 2049, remote_ip="203.0.113.10")

    assert empty == TurnstileVerificationResult(success=False)
    assert oversized == TurnstileVerificationResult(success=False)
    assert calls == 0
