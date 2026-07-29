from __future__ import annotations

import pytest

from waf_runtime.render import render_candidate


def test_empty_candidate_is_stable() -> None:
    result = render_candidate(4, [])
    assert result.content == "# PR7 dynamic WAF candidate\n"
    assert result.checksum_sha256


def test_rules_are_sorted_and_have_fixed_ids() -> None:
    items = [
        {
            "entry_id": 2,
            "recommendation_id": 9,
            "source_ip": "203.0.113.8",
            "request_path": "/records/search",
            "expires_at": "2026-07-29T00:00:02.000Z",
        },
        {
            "entry_id": 1,
            "recommendation_id": 8,
            "source_ip": "203.0.113.7",
            "request_path": "/records/search",
            "expires_at": "2026-07-29T00:00:01.000Z",
        },
    ]
    result = render_candidate(4, items)
    assert "id:10000" in result.content
    assert "id:10001" in result.content
    assert result.content.index("203.0.113.7") < result.content.index("203.0.113.8")
    assert result.content.endswith("\n")
    assert "@lt 1785283200" in result.content


def test_renderer_rejects_more_than_512_entries() -> None:
    items = [
        {
            "entry_id": i,
            "recommendation_id": i,
            "source_ip": f"10.0.0.{i % 250 + 1}",
            "request_path": "/records/search",
            "expires_at": "2026-07-29T00:00:01.000Z",
        }
        for i in range(1, 514)
    ]
    with pytest.raises(ValueError, match="512"):
        render_candidate(4, items)
