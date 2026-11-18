"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from the project root .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


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
    return int(value.strip())


class Settings(BaseModel):
    """Centralized application settings."""

    app_name: str = _get_str_env("APP_NAME", "AI Website Link Analysis API")
    app_version: str = _get_str_env("APP_VERSION", "1.0.0")
    app_description: str = _get_str_env(
        "APP_DESCRIPTION",
        (
            "An AI-powered FastAPI backend that accepts a website URL, extracts "
            "website content, and generates structured business, competitor, SEO, "
            "search query, service, and target audience insights."
        ),
    )

    request_timeout: int = _get_int_env("REQUEST_TIMEOUT", 15)
    max_content_length: int = _get_int_env("MAX_CONTENT_LENGTH", 15000)

    llm_provider: str = _get_str_env("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "").strip()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()


settings = Settings()

