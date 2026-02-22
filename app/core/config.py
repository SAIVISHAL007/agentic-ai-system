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
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)

    # Agent Configuration
    MAX_REASONING_STEPS: int = int(os.getenv("MAX_REASONING_STEPS", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # Memory Configuration
    MEMORY_TYPE: str = os.getenv("MEMORY_TYPE", "in_memory")  # in_memory or file

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are configured."""
        if cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")


settings = Settings()
