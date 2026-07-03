import re

from web_app.observability.context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_span_id,
    get_trace_id,
    is_valid_request_id,
    parse_traceparent,
    reset_request_context,
    set_request_context,
)


def test_request_context_can_be_set_and_reset():
    tokens = set_request_context(
        request_id="request-123",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
    )

    assert get_request_id() == "request-123"
    assert get_trace_id() == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert get_span_id() == "00f067aa0ba902b7"

    reset_request_context(tokens)

    assert get_request_id() is None
    assert get_trace_id() is None
    assert get_span_id() is None


def test_request_id_validation_accepts_only_safe_bounded_characters():
    assert is_valid_request_id("req.A_B-9:child")
    assert is_valid_request_id("a" * 128)

    assert not is_valid_request_id("")
    assert not is_valid_request_id("a" * 129)
    assert not is_valid_request_id("request id")
    assert not is_valid_request_id("request\nforged")
    assert not is_valid_request_id("request/unsafe")


def test_generated_request_id_is_safe_and_unique():
    first = generate_request_id()
    second = generate_request_id()

    assert first != second
    assert is_valid_request_id(first)
    assert is_valid_request_id(second)


def test_generated_trace_id_is_nonzero_lowercase_hex():
    trace_id = generate_trace_id()

    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    assert trace_id != "0" * 32


def test_parse_traceparent_preserves_valid_trace_and_span_ids():
    parsed = parse_traceparent(
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    )

    assert parsed == (
        "4bf92f3577b34da6a3ce929d0e0e4736",
        "00f067aa0ba902b7",
    )


def test_parse_traceparent_rejects_invalid_or_unsupported_values():
    invalid_values = [
        "",
        "01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "00-00000000000000000000000000000000-00f067aa0ba902b7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",
        "00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa0ba902b7-01",
        "00-too-short-00f067aa0ba902b7-01",
        "request\nforged",
    ]

    assert all(parse_traceparent(value) is None for value in invalid_values)
