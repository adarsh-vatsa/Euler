from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    database_url: str = f"sqlite:///{REPO_DIR / 'data' / 'euler.db'}"
    model_generation: str = "claude-opus-4-7"
    model_fast: str = "claude-haiku-4-5-20251001"


settings = Settings()
