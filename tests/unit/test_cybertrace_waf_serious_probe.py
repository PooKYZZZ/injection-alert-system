import cybertrace_waf_serious_probe as probe


def test_cloudflare_access_headers_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "client-secret-test")

    assert probe.cloudflare_access_headers() == {
        "CF-Access-Client-Id": "client-id-test",
        "CF-Access-Client-Secret": "client-secret-test",
    }


def test_cloudflare_access_headers_are_empty_when_unconfigured(monkeypatch):
    monkeypatch.delenv("CF_ACCESS_CLIENT_ID", raising=False)
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)

    assert probe.cloudflare_access_headers() == {}
