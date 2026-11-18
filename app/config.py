"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from the project root .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _get_list_env(key: str, default: list[str]) -> list[str]:
    """Return a comma-separated list of non-empty strings from an environment variable."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return list(default)
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items if items else list(default)


def _get_str_env(key: str, default: str) -> str:
    """Return a non-empty string environment variable or a default value."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_int_env(key: str, default: int) -> int:
    """Return an integer environment variable or a default value."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"Environment variable '{key}' must be a valid integer.") from exc


def _get_float_env(key: str, default: float) -> float:
    """Return a float environment variable or a default value."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value.strip())
    except ValueError as exc:
        raise ValueError(f"Environment variable '{key}' must be a valid number.") from exc


def _resolve_gemini_model() -> str:
    """Resolve the configured Gemini model without silently switching at runtime."""
    explicit_gemini_model = os.getenv("GEMINI_MODEL", "").strip()
    if explicit_gemini_model:
        return explicit_gemini_model
    legacy_llm_model = os.getenv("LLM_MODEL", "").strip()
    if legacy_llm_model:
        return legacy_llm_model
    return DEFAULT_GEMINI_MODEL


class Settings(BaseModel):
    """Centralized application settings with range validation."""

    app_name: str = Field(default="AI Website Link Analysis API", min_length=1)
    app_version: str = Field(default="1.0.0", min_length=1)
    app_description: str = Field(
        default=(
            "An AI-powered FastAPI backend that accepts a website URL, extracts "
            "website content, and generates structured business, competitor, SEO, "
            "search query, service, and target audience insights."
        ),
        min_length=1,
    )

    request_timeout: int = Field(default=15, gt=0)
    max_content_length: int = Field(default=15000, gt=0)
    max_response_bytes: int = Field(default=2_097_152, gt=0)
    user_agent: str = Field(default="AIWebsiteLinkAnalysisBot/1.0", min_length=1)
    cors_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))

    gemini_api_key: str = ""
    gemini_model: str = Field(default=DEFAULT_GEMINI_MODEL, min_length=1)
    llm_timeout_seconds: float = Field(default=45.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_retry_base_delay: float = Field(default=1.0, ge=0)
    llm_max_output_tokens: int = Field(default=4096, gt=0)


def load_settings() -> Settings:
    """Construct and validate Settings from the current process environment."""
    return Settings(
        app_name=_get_str_env("APP_NAME", "AI Website Link Analysis API"),
        app_version=_get_str_env("APP_VERSION", "1.0.0"),
        app_description=_get_str_env(
            "APP_DESCRIPTION",
            (
                "An AI-powered FastAPI backend that accepts a website URL, extracts "
                "website content, and generates structured business, competitor, SEO, "
                "search query, service, and target audience insights."
            ),
        ),
        request_timeout=_get_int_env("REQUEST_TIMEOUT", 15),
        max_content_length=_get_int_env("MAX_CONTENT_LENGTH", 15000),
        max_response_bytes=_get_int_env("MAX_RESPONSE_BYTES", 2_097_152),
        user_agent=_get_str_env("USER_AGENT", "AIWebsiteLinkAnalysisBot/1.0"),
        cors_origins=_get_list_env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=_resolve_gemini_model(),
        llm_timeout_seconds=_get_float_env("LLM_TIMEOUT_SECONDS", 45.0),
        llm_max_retries=_get_int_env("LLM_MAX_RETRIES", 2),
        llm_retry_base_delay=_get_float_env("LLM_RETRY_BASE_DELAY", 1.0),
        llm_max_output_tokens=_get_int_env("LLM_MAX_OUTPUT_TOKENS", 4096),
    )


settings = load_settings()
