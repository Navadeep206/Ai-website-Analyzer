"""Configuration loading and validation tests (Phase 7 QA)."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from app.config import DEFAULT_GEMINI_MODEL, load_settings


class TestConfigurationLoading:
    """Verify environment variable parsing, defaults, precedence, and bounds."""

    def test_defaults_succeed_without_gemini_api_key(self, monkeypatch):
        for var in (
            "GEMINI_API_KEY",
            "GEMINI_MODEL",
            "LLM_MODEL",
            "REQUEST_TIMEOUT",
            "MAX_CONTENT_LENGTH",
            "MAX_RESPONSE_BYTES",
            "LLM_TIMEOUT_SECONDS",
            "LLM_MAX_RETRIES",
            "LLM_RETRY_BASE_DELAY",
            "LLM_MAX_OUTPUT_TOKENS",
        ):
            monkeypatch.delenv(var, raising=False)

        cfg = load_settings()
        assert cfg.gemini_api_key == ""
        assert cfg.gemini_model == DEFAULT_GEMINI_MODEL
        assert cfg.request_timeout == 15
        assert cfg.max_content_length == 15000
        assert cfg.max_response_bytes == 2_097_152
        assert cfg.llm_timeout_seconds == 45.0
        assert cfg.llm_max_retries == 2
        assert cfg.llm_retry_base_delay == 1.0
        assert cfg.llm_max_output_tokens == 4096

    def test_gemini_model_takes_precedence_over_legacy_llm_model(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash-lite")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
        assert load_settings().gemini_model == "gemini-3.6-flash"

        monkeypatch.setenv("GEMINI_MODEL", "")
        assert load_settings().gemini_model == "gemini-2.5-flash-lite"

    @pytest.mark.parametrize(
        ("env_key", "bad_value"),
        [
            ("REQUEST_TIMEOUT", "0"),
            ("REQUEST_TIMEOUT", "-5"),
            ("REQUEST_TIMEOUT", "not-an-int"),
            ("MAX_CONTENT_LENGTH", "0"),
            ("MAX_RESPONSE_BYTES", "-100"),
            ("LLM_TIMEOUT_SECONDS", "0"),
            ("LLM_TIMEOUT_SECONDS", "abc"),
            ("LLM_MAX_RETRIES", "-1"),
            ("LLM_RETRY_BASE_DELAY", "-0.5"),
            ("LLM_MAX_OUTPUT_TOKENS", "0"),
        ],
    )
    def test_invalid_numeric_settings_rejected_cleanly(
        self, monkeypatch, env_key: str, bad_value: str
    ):
        monkeypatch.setenv(env_key, bad_value)
        with pytest.raises((ValueError, ValidationError)):
            load_settings()

