"""LLM model provider abstraction using LangChain Google GenAI."""
import logging
import warnings
from typing import Any

# Filter benign UserWarning from lite models that use fixed sampling defaults (ignore temperature).
warnings.filterwarnings("ignore", category=UserWarning, message=r".*uses fixed sampling defaults.*")

from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from src.config import settings
from src.core import metrics
from src.core.log_context import exc_brief
from src.core.tracing import set_attributes, span

logger = logging.getLogger("multiagent.llm")


class LLMNotConfiguredError(Exception):
    """Raised when the LLM is invoked but GEMINI_API_KEY is not configured."""


class LLMConfigurationError(Exception):
    """Raised for non-retryable configuration errors (missing model, bad key, permission, invalid request)."""


class LLMUnavailableError(Exception):
    """Raised when the external LLM service is unreachable, times out, or fails."""


def _build_chat_model(
    model_name: str,
    timeout_s: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """Build a chat model instance for the configured provider and model name."""
    eff_timeout = settings.LLM_TIMEOUT_S if timeout_s is None else timeout_s
    eff_retries = settings.LLM_MAX_RETRIES if max_retries is None else max_retries

    provider = settings.LLM_PROVIDER
    if provider == "google_genai":
        if not settings.GEMINI_API_KEY:
            raise LLMNotConfiguredError("GEMINI_API_KEY is not configured.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            timeout=eff_timeout,
            max_retries=eff_retries,
        )

    raise LLMConfigurationError(f"unsupported LLM_PROVIDER '{provider}'")


def get_chat_model(
    model_name: str | None = None,
    timeout_s: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """
    Return the configured BaseChatModel for the primary model.
    Uses model_name if provided, otherwise settings.LLM_MODEL.
    """
    name = model_name or settings.LLM_MODEL
    return _build_chat_model(name, timeout_s=timeout_s, max_retries=max_retries)


def get_fallback_model() -> BaseChatModel | None:
    """
    Return the configured fallback model, or None if LLM_FALLBACK_MODEL is empty.
    """
    fb_name = settings.LLM_FALLBACK_MODEL
    if not fb_name:
        return None
    return _build_chat_model(fb_name)


def get_embedder(task_type: str) -> GoogleGenerativeAIEmbeddings:
    """
    Return configured GoogleGenerativeAIEmbeddings instance.
    Raises LLMNotConfiguredError if GEMINI_API_KEY is not configured.
    """
    if not settings.GEMINI_API_KEY:
        raise LLMNotConfiguredError("GEMINI_API_KEY is not configured.")
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        task_type=task_type,
        output_dimensionality=settings.EMBEDDING_DIM,
    )


def extract_model_name(model: Any) -> str:
    """Extract model identifier from ChatModel or RunnableBinding."""
    target = getattr(model, "bound", model)
    return (
        getattr(target, "model_name", None)
        or getattr(target, "model", None)
        or getattr(target, "_llm_type", None)
        or getattr(model, "model_name", None)
        or getattr(model, "model", None)
        or getattr(model, "_llm_type", "unknown")
    )


def _token_span_attrs(ai_message: Any) -> dict[str, int]:
    usage = getattr(ai_message, "usage_metadata", None)
    if not isinstance(usage, dict):
        return {}
    attrs: dict[str, int] = {}
    if usage.get("input_tokens") is not None:
        attrs["llm.input_tokens"] = int(usage["input_tokens"])
    if usage.get("output_tokens") is not None:
        attrs["llm.output_tokens"] = int(usage["output_tokens"])
    return attrs


def invoke_model_with_fallback(
    bound_model: Any,
    bound_fallback: Any | None,
    messages: list[BaseMessage],
    trace_id: str = "",
    caller_name: str = "Supervisor",
) -> tuple[AIMessage, Any]:
    """
    Invoke bound primary model with automatic failover to bound fallback on transient errors.
    Returns (ai_message, active_model).
    """
    primary_name = extract_model_name(bound_model)
    with span(
        "llm.call",
        {
            "llm.caller": caller_name,
            "llm.model": primary_name,
            "llm.fallback_used": False,
        },
    ):
        try:
            ai_message = bound_model.invoke(messages)
            metrics.inc_llm_call(caller_name, "ok")
            set_attributes(
                {
                    "llm.model": primary_name,
                    "llm.fallback_used": False,
                    "llm.status": "ok",
                    **_token_span_attrs(ai_message),
                }
            )
            return ai_message, bound_model
        except (LLMNotConfiguredError, LLMConfigurationError):
            metrics.inc_llm_call(caller_name, "error")
            set_attributes({"llm.model": primary_name, "llm.fallback_used": False, "llm.status": "error"})
            raise
        except (
            ModelNotFoundError,
            ModelAuthenticationError,
            ModelPermissionDeniedError,
            ModelInvalidRequestError,
        ) as exc:
            logger.error(f"{caller_name} primary model configuration error [trace_id={trace_id}]: {exc_brief(exc)}")
            metrics.inc_llm_call(caller_name, "error")
            set_attributes({"llm.model": primary_name, "llm.fallback_used": False, "llm.status": "error"})
            raise LLMConfigurationError(str(exc)) from exc
        except Exception as exc:
            if bound_fallback is not None:
                fb_name = extract_model_name(bound_fallback)
                logger.warning(
                    f"Primary model '{primary_name}' failed with {exc_brief(exc)}. "
                    f"Failing over to fallback [trace_id={trace_id}]."
                )
                try:
                    ai_message = bound_fallback.invoke(messages)
                    metrics.inc_llm_call(caller_name, "fallback")
                    set_attributes(
                        {
                            "llm.model": fb_name,
                            "llm.fallback_used": True,
                            "llm.status": "ok",
                            **_token_span_attrs(ai_message),
                        }
                    )
                    return ai_message, bound_fallback
                except (LLMNotConfiguredError, LLMConfigurationError):
                    metrics.inc_llm_call(caller_name, "error")
                    set_attributes({"llm.model": fb_name, "llm.fallback_used": True, "llm.status": "error"})
                    raise
                except (
                    ModelNotFoundError,
                    ModelAuthenticationError,
                    ModelPermissionDeniedError,
                    ModelInvalidRequestError,
                ) as fb_cfg_err:
                    logger.error(
                        f"{caller_name} fallback model configuration error [trace_id={trace_id}]: {exc_brief(fb_cfg_err)}"
                    )
                    metrics.inc_llm_call(caller_name, "error")
                    set_attributes({"llm.model": fb_name, "llm.fallback_used": True, "llm.status": "error"})
                    raise LLMConfigurationError(str(fb_cfg_err)) from fb_cfg_err
                except Exception as fb_exc:
                    logger.error(
                        f"Both primary ('{primary_name}') and fallback ('{fb_name}') models failed "
                        f"[trace_id={trace_id}]: {exc_brief(fb_exc)}"
                    )
                    metrics.inc_llm_call(caller_name, "error")
                    set_attributes({"llm.model": fb_name, "llm.fallback_used": True, "llm.status": "error"})
                    raise LLMUnavailableError(str(fb_exc)) from fb_exc
            else:
                logger.error(f"{caller_name} primary model invocation failed [trace_id={trace_id}]: {exc_brief(exc)}")
                metrics.inc_llm_call(caller_name, "error")
                set_attributes({"llm.model": primary_name, "llm.fallback_used": False, "llm.status": "error"})
                raise LLMUnavailableError(str(exc)) from exc
