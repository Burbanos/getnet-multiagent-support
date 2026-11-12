"""Application configuration using Pydantic Settings and structured logging."""
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System configuration parameters loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    LOG_HASH_SALT: str = ""

    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "google_genai"
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_FALLBACK_MODEL: str = "gemini-3.1-flash-lite"
    LLM_TIMEOUT_S: float = 30.0
    LLM_MAX_RETRIES: int = 2
    MAX_SUPERVISOR_STEPS: int = 6
    MAX_SPECIALIST_STEPS: int = 4

    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 3
    DDGS_TIMEOUT: int = 8
    PUBLIC_DATA_TIMEOUT_S: float = 8.0
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIM: int = 768
    RAG_TOP_K: int = 4
    RAG_MIN_SCORE: float = 0.61
    RAG_MIN_CHUNK_CHARS: int = 120
    RAG_RERANK_ENABLED: bool = True
    RAG_RERANK_MODEL: str = ""
    RAG_RERANK_TIMEOUT_S: float = 10.0
    RAG_DENSE_CANDIDATES: int = 6
    RAG_LEXICAL_CANDIDATES: int = 6
    RAG_RERANK_MIN_RELEVANCE: int = 2
    RAG_RRF_K: int = 60
    INDEX_DIR: str = "data/index"

    ENABLE_GUARDRAILS: bool = True
    GUARDRAIL_CLASSIFIER_ENABLED: bool = True
    GUARDRAIL_CLASSIFIER_MODEL: str = ""  # empty -> LLM_MODEL
    GUARDRAIL_CLASSIFIER_TIMEOUT_S: float = 10.0
    GUARDRAIL_CLASSIFIER_FAIL_MODE: Literal["open", "closed"] = "open"
    API_KEYS: str = ""
    RATE_LIMIT_PER_MINUTE: int = 30
    CHECKPOINT_DB_PATH: str = "data/checkpoints.db"
    TICKETS_DB_PATH: str = "data/tickets.db"
    ESCALATE_AFTER_ABSTENTIONS: int = 2
    OPERATOR_WEBHOOK_URL: str = ""
    OPERATOR_WEBHOOK_TIMEOUT_S: float = 3.0
    PUBLIC_BASE_URL: str = ""
    MAX_HISTORY_MESSAGES: int = 40
    EVAL_JUDGE_MODEL: str = "gemini-3.1-flash-lite"
    EVAL_SLEEP_S: float = 6.0


settings = Settings()


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request-scoped context: trace_id, session_id, user_hash
        try:
            from src.core.log_context import current, user_hash

            ctx = current()
            for k, v in ctx.items():
                log_obj[k] = v
        except ImportError:
            pass

        # Add supported extras when present
        for field in ("agent", "node", "tool", "status", "latency_ms", "execution_time_ms"):
            if hasattr(record, field):
                log_obj[field] = getattr(record, field)

        # Never log raw user_id: if user_id extra is passed, map to user_hash
        if hasattr(record, "user_id") and "user_hash" not in log_obj:
            from src.core.log_context import user_hash

            raw_uid = record.user_id
            if raw_uid is not None:
                log_obj["user_hash"] = user_hash(str(raw_uid))

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(name: str = "multiagent") -> logging.Logger:
    """Initialize and configure structured application logger."""
    logger_instance = logging.getLogger(name)
    if not logger_instance.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger_instance.addHandler(handler)
        logger_instance.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        logger_instance.propagate = False
    return logger_instance


logger = setup_logger()
