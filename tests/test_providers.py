"""Tests for the provider layer, fallback model mechanism, and bank account masking."""
from typing import Any

import pytest
from langchain_core.exceptions import (
    ModelNotFoundError,
    ModelRateLimitError,
)
from langchain_core.messages import AIMessage

from src.config import settings
from src.core.graph import OrchestrationGraph
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    get_chat_model,
    get_fallback_model,
)
from src.core.pii import mask_bank_account
from tests.fakes import ScriptedChatModel


class RaisingChatModel(ScriptedChatModel):
    """Fake chat model that raises a configured exception upon invocation."""

    exc: Any = None

    def __init__(self, exc: Any = None, **kwargs: Any):
        super().__init__(**kwargs)
        object.__setattr__(self, "exc", exc)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        raise self.exc


class NamedFakeModel(ScriptedChatModel):
    """Fake model with an identifiable model name attribute."""

    model: str = "fake-fallback-model"


def test_provider_defaults():
    """Verify standard default settings for provider, model, and fallback model."""
    assert settings.LLM_PROVIDER == "google_genai"
    assert settings.LLM_MODEL == "gemini-3.5-flash"
    assert settings.LLM_FALLBACK_MODEL == "gemini-3.5-flash-lite"


def test_get_chat_model_respects_model_override():
    """Verify get_chat_model allows overriding model_name."""
    saved_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = "dummy-key-for-test"
        model = get_chat_model("custom-override-model")
        assert "custom-override-model" in str(getattr(model, "model", ""))
    finally:
        settings.GEMINI_API_KEY = saved_key


def test_get_fallback_model_returns_none_when_empty():
    """Verify get_fallback_model returns None when LLM_FALLBACK_MODEL is empty."""
    saved_fallback = settings.LLM_FALLBACK_MODEL
    try:
        settings.LLM_FALLBACK_MODEL = ""
        assert get_fallback_model() is None
    finally:
        settings.LLM_FALLBACK_MODEL = saved_fallback


def test_unknown_provider_raises_configuration_error():
    """Verify unsupported provider strings raise LLMConfigurationError."""
    saved_provider = settings.LLM_PROVIDER
    try:
        settings.LLM_PROVIDER = "foo"
        with pytest.raises(LLMConfigurationError) as exc_info:
            get_chat_model()
        assert "unsupported LLM_PROVIDER 'foo'" in str(exc_info.value)
    finally:
        settings.LLM_PROVIDER = saved_provider


def test_missing_optional_provider_packages_raise_configuration_error():
    """Verify selecting openai or anthropic raises LLMConfigurationError with package install advice."""
    saved_provider = settings.LLM_PROVIDER
    try:
        for prov in ("openai", "anthropic"):
            settings.LLM_PROVIDER = prov
            with pytest.raises(LLMConfigurationError) as exc_info:
                get_chat_model()
            err_msg = str(exc_info.value)
            assert f"langchain_{prov}" in err_msg or f"langchain-{prov}" in err_msg
    finally:
        settings.LLM_PROVIDER = saved_provider


def test_missing_api_key_raises_not_configured_error():
    """Verify missing API key raises LLMNotConfiguredError."""
    saved_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = ""
        with pytest.raises(LLMNotConfiguredError) as exc_info:
            get_chat_model()
        assert "GEMINI_API_KEY" in str(exc_info.value)
    finally:
        settings.GEMINI_API_KEY = saved_key


def test_transient_error_uses_fallback_model():
    """Verify graph switches to fallback model on rate limit error and reports model name."""
    primary = RaisingChatModel(exc=ModelRateLimitError("Quota exceeded (429)"))
    fallback = NamedFakeModel(
        model="gemini-3.5-flash-lite",
        responses=[AIMessage(content="Resposta gerada pelo modelo reserva.")],
    )
    orch = OrchestrationGraph(chat_model=primary, fallback_model=fallback)
    state = orch.run_sync(user_id="cliente1988", message="oi", session_id="test-transient-fb")

    assert state.agent_response == "Resposta gerada pelo modelo reserva."
    assert state.llm_model == "gemini-3.5-flash-lite"
    assert len(primary.received) == 1
    assert len(fallback.received) == 1


def test_configuration_error_does_not_use_fallback():
    """Verify graph does NOT attempt fallback when primary raises ModelNotFoundError."""
    primary = RaisingChatModel(exc=ModelNotFoundError("Model not found"))
    fallback = NamedFakeModel(
        model="gemini-3.5-flash-lite",
        responses=[AIMessage(content="Não deve ser chamado")],
    )
    orch = OrchestrationGraph(chat_model=primary, fallback_model=fallback)

    with pytest.raises(LLMConfigurationError):
        orch.run_sync(user_id="cliente1988", message="oi", session_id="test-cfg-nofb")

    assert len(primary.received) == 1
    assert len(fallback.received) == 0


def test_bank_account_masking():
    """Verify bank account masking preserves only designated characters and leaves non-account text intact."""
    # Standard format from mock_db
    raw = "Santander (033) Ag: 1234 CC: 98765-4"
    masked = mask_bank_account(raw)
    assert masked == "Santander (033) Ag: **** CC: ***65-4"

    # Alternative spellings
    assert mask_bank_account("Agência: 0001 CC: 12345-6") == "Agência: **** CC: ***45-6"
    assert mask_bank_account("Ag. 4321 C/C: 87654-X") == "Ag. **** C/C: ***54-X"
    assert mask_bank_account("Conta Corrente: 98765-4") == "Conta Corrente: ***65-4"

    # Preserves non-account text
    plain = "Olá, gostaria de saber informações sobre as taxas da maquininha."
    assert mask_bank_account(plain) == plain

    # Fail-safe empty/none
    assert mask_bank_account("") == ""
    assert mask_bank_account(None) is None  # type: ignore[arg-type]
