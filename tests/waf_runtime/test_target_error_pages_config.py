from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_target_error_pages_are_internal_and_cover_edge_statuses():
    config = (
        ROOT
        / "config"
        / "modsecurity"
        / "target-error-pages-location-common.conf.template"
    ).read_text(encoding="utf-8")

    for status in (403, 500, 502, 503, 504):
        assert f"error_page {status} /cybertrace-errors/{status}.html;" in config
        page = (
            ROOT
            / "config"
            / "modsecurity"
            / "target-error-pages"
            / f"{status}.html"
        )
        assert page.is_file()
        page_markup = page.read_text(encoding="utf-8")
        assert "cybertrace-error-page.css" in page_markup
        assert '<meta name="referrer" content="no-referrer">' in page_markup

    stylesheet = (
        ROOT
        / "config"
        / "modsecurity"
        / "target-error-pages"
        / "cybertrace-error-page.css"
    )
    assert stylesheet.is_file()

    assert "location ^~ /cybertrace-errors/ {\n    internal;" in config
    assert "access_log /dev/null combined;" in config
    assert 'add_header Referrer-Policy "no-referrer" always;' in config
    assert "X-CyberTrace-Transaction-ID $request_id always" in config


def test_target_error_pages_do_not_intercept_upstream_responses():
    proxy = (
        ROOT
        / "config"
        / "modsecurity"
        / "source-correlation-proxy-backend.conf.template"
    ).read_text(encoding="utf-8")
    assert "proxy_intercept_errors on" not in proxy.lower()


def test_target_error_pages_are_mounted_read_only():
    compose = (ROOT / "docker-compose.demo-target.yml").read_text(encoding="utf-8")
    assert (
        "target-error-pages-location-common.conf.template:/etc/nginx/templates/includes/location_common.conf.template:ro"
        in compose
    )
    assert (
        "config/modsecurity/target-error-pages:/usr/share/nginx/html/cybertrace-errors:ro"
        in compose
    )
