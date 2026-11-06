"""LLM model provider abstraction using LangChain Google GenAI."""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings


class LLMNotConfiguredError(Exception):
    """Raised when the LLM is invoked but GEMINI_API_KEY is not configured."""


class LLMConfigurationError(Exception):
    """Raised for non-retryable configuration errors (missing model, bad key, permission, invalid request)."""


class LLMUnavailableError(Exception):
    """Raised when the external LLM service is unreachable, times out, or fails."""


def _build_chat_model(model_name: str) -> BaseChatModel:
    """Build a chat model instance for the configured provider and model name."""
    provider = settings.LLM_PROVIDER
    if provider == "google_genai":
        if not settings.GEMINI_API_KEY:
            raise LLMNotConfiguredError("GEMINI_API_KEY is not configured.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            timeout=settings.LLM_TIMEOUT_S,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    if provider in {"openai", "anthropic"}:
        if provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise LLMConfigurationError(
                    f"install langchain-{provider} to use LLM_PROVIDER={provider}"
                ) from exc
            return ChatOpenAI(
                model=model_name,
                temperature=0,
                timeout=settings.LLM_TIMEOUT_S,
                max_retries=settings.LLM_MAX_RETRIES,
            )
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise LLMConfigurationError(
                f"install langchain-{provider} to use LLM_PROVIDER={provider}"
            ) from exc
        return ChatAnthropic(
            model=model_name,
            temperature=0,
            timeout=settings.LLM_TIMEOUT_S,
            max_retries=settings.LLM_MAX_RETRIES,
        )

    raise LLMConfigurationError(f"unsupported LLM_PROVIDER '{provider}'")


def get_chat_model(model_name: str | None = None) -> BaseChatModel:
    """
    Return the configured BaseChatModel for the primary model.
    Uses model_name if provided, otherwise settings.LLM_MODEL.
    """
    name = model_name or settings.LLM_MODEL
    return _build_chat_model(name)


def get_fallback_model() -> BaseChatModel | None:
    """
    Return the configured fallback model, or None if LLM_FALLBACK_MODEL is empty.
    """
    fb_name = settings.LLM_FALLBACK_MODEL
    if not fb_name:
        return None
    return _build_chat_model(fb_name)
