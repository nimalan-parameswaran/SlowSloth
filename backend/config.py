"""Configuration module for SlowSloth."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings with environment variable override support."""

    HOST: str = Field(default="127.0.0.1", description="Host interface to bind")
    PORT: int = Field(default=8000, description="Port number to listen on")
    DB_PATH: str = Field(default="data/slowsloth.db", description="Path to SQLite database file")
    TIMEZONE: str = Field(default="Asia/Kolkata", description="Configured local timezone")

    # AI backend settings
    AI_BACKEND: str = Field(
        default="dev_mock",
        description="Active AI backend: dev_mock | llama_cpp | ollama",
    )
    AI_MODEL_IDENTIFIER: str = Field(
        default="deterministic-rule-parser",
        description="Model identifier or filename",
    )
    INFERENCE_ENDPOINT: str = Field(
        default="http://127.0.0.1:8080",
        description="Local inference server URL (e.g. llama-server or Ollama)",
    )
    INFERENCE_TIMEOUT_SEC: int = Field(
        default=45,
        description="Timeout for inference requests in seconds",
    )
    CONTEXT_LIMIT: int = Field(
        default=2048,
        description="Maximum context window in tokens",
    )
    ALLOW_DEV_FALLBACK: bool = Field(
        default=True,
        description="Fallback to rule-based mock engine if local AI engine is unavailable",
    )

    # Security & LAN settings
    ENABLE_LAN_ACCESS: bool = Field(
        default=False,
        description="Explicit toggle for exposing beyond localhost",
    )
    LAN_API_KEY: Optional[str] = Field(
        default=None,
        description="API key required for LAN access when enabled",
    )

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment variables with sensible defaults."""
        return cls(
            HOST=os.getenv("SLOWSLOTH_HOST", "127.0.0.1"),
            PORT=int(os.getenv("SLOWSLOTH_PORT", "8000")),
            DB_PATH=os.getenv("SLOWSLOTH_DB_PATH", "data/slowsloth.db"),
            TIMEZONE=os.getenv("SLOWSLOTH_TIMEZONE", "Asia/Kolkata"),
            AI_BACKEND=os.getenv("AI_BACKEND", "dev_mock"),
            AI_MODEL_IDENTIFIER=os.getenv(
                "AI_MODEL_IDENTIFIER", "deterministic-rule-parser"
            ),
            INFERENCE_ENDPOINT=os.getenv(
                "INFERENCE_ENDPOINT", "http://127.0.0.1:8080"
            ),
            INFERENCE_TIMEOUT_SEC=int(os.getenv("INFERENCE_TIMEOUT_SEC", "45")),
            CONTEXT_LIMIT=int(os.getenv("CONTEXT_LIMIT", "2048")),
            ALLOW_DEV_FALLBACK=os.getenv(
                "ALLOW_DEV_FALLBACK", "true"
            ).lower()
            in ("1", "true", "yes"),
            ENABLE_LAN_ACCESS=os.getenv(
                "ENABLE_LAN_ACCESS", "false"
            ).lower()
            in ("1", "true", "yes"),
            LAN_API_KEY=os.getenv("LAN_API_KEY") or None,
        )

    def get_absolute_db_path(self, base_dir: Optional[Path] = None) -> Path:
        """Resolve database path relative to base directory if not absolute."""
        path = Path(self.DB_PATH)
        if path.is_absolute():
            return path
        if base_dir is None:
            base_dir = Path.cwd()
        return (base_dir / path).resolve()


settings = Settings.load()
