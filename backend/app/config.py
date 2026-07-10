"""Configuration applicative (variables d'environnement)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOTO_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/yoto_bridge.sqlite"
    sync_interval_seconds: int = 3600
    stream_default_bitrate: int = 192
    stream_format: str = "mp3"
    # Fenêtre pendant laquelle une même piste ré-interrogée (requêtes Range,
    # reprises) renvoie le même morceau au lieu d'en choisir un nouveau.
    resolution_ttl_seconds: int = 8
    cors_origins: str = "*"


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
