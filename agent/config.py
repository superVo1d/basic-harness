"""Application configurational file."""

from __future__ import annotations
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_PATH = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings."""

    base_path: Path = BASE_PATH
    tavily_api_key: str = None
    max_context_size: int = 80_000
    protect_last_n: int = 10

    model_config = SettingsConfigDict(env_file=".env")
