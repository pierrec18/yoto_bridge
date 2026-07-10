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

    # Base publique du serveur, utilisée pour les URLs de stream déposées sur la
    # Yoto et pour l'URL de redirection OAuth. Ex : https://yotobridge.crvsk.me
    public_base_url: str = "http://localhost:8000"

    # Intégration API officielle Yoto (§18).
    yoto_login_base: str = "https://login.yotoplay.com"
    yoto_api_base: str = "https://api.yotoplay.com"
    yoto_audience: str = "https://api.yotoplay.com"
    yoto_scopes: str = "user:content:manage offline_access"

    # Protection optionnelle de l'interface et de l'API via OpenID Connect.
    auth_enabled: bool = False
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = "openid profile email"
    session_secret: str = ""
    session_max_age_seconds: int = 604800


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
