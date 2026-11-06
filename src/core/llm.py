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


def get_chat_model() -> BaseChatModel:
    """
    Return the configured ChatGoogleGenerativeAI model.
    Raises LLMNotConfiguredError if GEMINI_API_KEY is empty.
    """
    if not settings.GEMINI_API_KEY:
        raise LLMNotConfiguredError("GEMINI_API_KEY is not configured.")

    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0,
        timeout=settings.LLM_TIMEOUT_S,
        max_retries=settings.LLM_MAX_RETRIES,
    )
