"""Application configuration using Pydantic Settings and structured logging."""
import json
import logging
import sys
from datetime import UTC, datetime

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

    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "google_genai"
    LLM_MODEL: str = "gemini-3.5-flash"
    LLM_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TIMEOUT_S: float = 30.0
    LLM_MAX_RETRIES: int = 2
    MAX_SUPERVISOR_STEPS: int = 6
    MAX_SPECIALIST_STEPS: int = 4

    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 3
    DDGS_TIMEOUT: int = 8
    KB_DATA_PATH: str = "data/getnet_kb.json"
    CHROMA_PERSIST_DIR: str = ""

    ENABLE_GUARDRAILS: bool = True
    CONFIDENCE_THRESHOLD_ESCALATION: float = 0.45


settings = Settings()


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "agent"):
            log_obj["agent"] = record.agent
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "execution_time_ms"):
            log_obj["execution_time_ms"] = record.execution_time_ms
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
