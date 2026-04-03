"""Configuration module for loading environment variables and settings."""

import os
from typing import Optional
from pathlib import Path

# Automatically load .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass  # python-dotenv not installed, skip


class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # groq or openai
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)

    # Agent Configuration
    MAX_REASONING_STEPS: int = int(os.getenv("MAX_REASONING_STEPS", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    LLM_PLANNER_MAX_TOKENS: int = int(os.getenv("LLM_PLANNER_MAX_TOKENS", "800"))
    LLM_REASONING_MAX_TOKENS: int = int(os.getenv("LLM_REASONING_MAX_TOKENS", "800"))
    LLM_VALIDATOR_MAX_TOKENS: int = int(os.getenv("LLM_VALIDATOR_MAX_TOKENS", "600"))
    HTTP_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_REQUEST_TIMEOUT_SECONDS", "10"))
    
    # Memory Configuration
    MEMORY_TYPE: str = os.getenv("MEMORY_TYPE", "in_memory")  # in_memory or file

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # API Security (optional; disabled by default to preserve current behavior)
    API_AUTH_ENABLED: bool = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
    API_AUTH_TOKEN: Optional[str] = os.getenv("API_AUTH_TOKEN")

    # Rate limiting (optional; disabled by default)
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

    # Multi-tenant controls (optional)
    REQUIRE_TENANT_HEADER: bool = os.getenv("REQUIRE_TENANT_HEADER", "false").lower() == "true"
    DEFAULT_TENANT_ID: str = os.getenv("DEFAULT_TENANT_ID", "default")

    # History backend
    HISTORY_BACKEND: str = os.getenv("HISTORY_BACKEND", "jsonl")  # jsonl | sqlite
    HISTORY_STORAGE_DIR: str = os.getenv("HISTORY_STORAGE_DIR", "./.execution_history")
    HISTORY_SQLITE_PATH: str = os.getenv("HISTORY_SQLITE_PATH", "./.execution_history/executions.db")

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are configured."""
        if cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        if cls.API_AUTH_ENABLED and not cls.API_AUTH_TOKEN:
            raise ValueError("API_AUTH_TOKEN is required when API_AUTH_ENABLED=true")
        if cls.HISTORY_BACKEND not in {"jsonl", "sqlite"}:
            raise ValueError("HISTORY_BACKEND must be either 'jsonl' or 'sqlite'")
        if cls.HTTP_REQUEST_TIMEOUT_SECONDS <= 0:
            raise ValueError("HTTP_REQUEST_TIMEOUT_SECONDS must be greater than 0")


settings = Settings()
