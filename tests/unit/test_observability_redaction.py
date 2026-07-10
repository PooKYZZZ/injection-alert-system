from copy import deepcopy

from web_app.observability.redaction import (
    REDACTED,
    redact_for_log,
    redact_mapping,
    redact_value,
)


def test_redact_value_matches_sensitive_keys_case_insensitively():
    assert redact_value("Authorization", "Bearer secret") == REDACTED
    assert redact_value("X-API-KEY", "secret-key") == REDACTED
    assert redact_value("NextAuth_Secret", "secret") == REDACTED
    assert redact_value("request_path", "/api/health") == "/api/health"


def test_redact_mapping_redacts_nested_sensitive_values_without_mutation():
    original = {
        "request_id": "req-1",
        "headers": {
            "Cookie": "session=secret",
            "content-type": "application/json",
        },
        "items": [
            {"password": "hunter2", "status": "failed"},
            {"database_url": "postgresql://user:pass@example/db"},
        ],
    }
    snapshot = deepcopy(original)

    redacted = redact_mapping(original)

    assert redacted == {
        "request_id": "req-1",
        "headers": {
            "Cookie": REDACTED,
            "content-type": "application/json",
        },
        "items": [
            {"password": REDACTED, "status": "failed"},
            {"database_url": REDACTED},
        ],
    }
    assert original == snapshot


def test_redact_for_log_preserves_list_and_tuple_shapes():
    value = ([{"token": "secret"}], ("safe", {"pwd": "secret"}))

    redacted = redact_for_log(value)

    assert redacted == ([{"token": REDACTED}], ("safe", {"pwd": REDACTED}))
    assert isinstance(redacted, tuple)
    assert isinstance(redacted[0], list)
    assert isinstance(redacted[1], tuple)


def test_redact_for_log_bounds_strings_and_unknown_objects():
    class UnsafeObject:
        def __str__(self):
            return "object:" + ("x" * 5000)

    long_string = "x" * 5000

    assert len(redact_for_log(long_string)) <= 1024
    assert len(redact_for_log(UnsafeObject())) <= 1024


def test_all_required_sensitive_key_variants_are_redacted():
    keys = [
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "secret_key",
        "credential",
        "private_key",
        "session",
        "session_id",
        "database_url",
        "db_url",
        "connection_string",
        "auth_secret",
        "nextauth_secret",
        "api_secret_key",
        "groq_api_key",
    ]

    assert all(redact_value(key.upper(), "sensitive") == REDACTED for key in keys)


def test_separator_and_case_variants_are_redacted_recursively():
    original = {
        "clientSecret": "client-secret",
        "nested": [
            {
                "Secret-Key": "secret-key",
                "privateKey": "private-key",
                "apiKey": "api-key",
                "safe": "visible",
            }
        ],
    }

    redacted = redact_for_log(original)

    assert redacted["clientSecret"] == REDACTED
    assert redacted["nested"][0]["Secret-Key"] == REDACTED
    assert redacted["nested"][0]["privateKey"] == REDACTED
    assert redacted["nested"][0]["apiKey"] == REDACTED
    assert redacted["nested"][0]["safe"] == "visible"


def test_cyclic_structures_are_bounded_without_mutation():
    original = {"request_id": "req-cycle"}
    original["self"] = original

    redacted = redact_for_log(original)

    assert redacted["request_id"] == "req-cycle"
    assert redacted["self"] == "<cycle detected>"
    assert original["self"] is original
