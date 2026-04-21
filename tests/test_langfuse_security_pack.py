"""Tests for the Langfuse security example pack."""

from langfuse_security_pack.tools import _redact_text


def test_redact_text_handles_prefixed_and_standalone_secrets():
    text = (
        "authorization=bearer abc123 "
        "api_key=secret-value "
        "sk-lf-763508c0-4d06-42d3-8caf-822506e03f46 "
        "pk-lf-d2838191-2f1f-4ac3-9cb8-f7d2ddff9c9f"
    )

    redacted = _redact_text(text)

    assert "abc123" not in redacted
    assert "secret-value" not in redacted
    assert "sk-lf-763508c0-4d06-42d3-8caf-822506e03f46" not in redacted
    assert "pk-lf-d2838191-2f1f-4ac3-9cb8-f7d2ddff9c9f" not in redacted
    assert redacted.count("[REDACTED]") == 4
