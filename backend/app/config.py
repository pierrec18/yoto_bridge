"""Configuration applicative (variables d'environnement)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOTO_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/yoto_bridge.sqlite"
    sync_interval_seconds: int = Field(default=3600, ge=60, le=86400)
    stream_default_bitrate: int = Field(default=192, ge=32, le=320)
    stream_format: str = "mp3"
    # Fenêtre pendant laquelle une même piste ré-interrogée (requêtes Range,
    # reprises) renvoie le même morceau au lieu d'en choisir un nouveau.
    resolution_ttl_seconds: int = Field(default=8, ge=1, le=300)
    # Vide = même origine que public_base_url. Un wildcard est volontairement
    # refusé avec OIDC actif (les cookies de session exigent une origine connue).
    cors_origins: str = ""

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
    session_max_age_seconds: int = Field(default=604800, ge=300, le=2592000)

    # Clé utilisée pour chiffrer les identifiants Navidrome, jetons Yoto et
    # token de streaming dans SQLite. Une valeur stable doit être conservée
    # dans le gestionnaire de secrets du déploiement.
    secrets_key: str = ""

    @model_validator(mode="after")
    def validate_security(self) -> "AppConfig":
        host = self.public_base_url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        local_url = host in {"localhost", "127.0.0.1", "[::1]"}
        if self.secrets_key and len(self.secrets_key) < 32:
            raise ValueError("YOTO_SECRETS_KEY doit contenir au moins 32 caractères")
        if not local_url and not self.secrets_key.strip():
            raise ValueError(
                "YOTO_SECRETS_KEY est obligatoire lorsque YOTO_PUBLIC_BASE_URL est externe"
            )
        if not local_url and not self.auth_enabled:
            raise ValueError(
                "YOTO_AUTH_ENABLED doit être true lorsque YOTO_PUBLIC_BASE_URL est externe"
            )
        if self.auth_enabled:
            missing = {
                "oidc_issuer_url": self.oidc_issuer_url,
                "oidc_client_id": self.oidc_client_id,
                "oidc_client_secret": self.oidc_client_secret,
                "session_secret": self.session_secret,
            }
            missing_names = [name for name, value in missing.items() if not value.strip()]
            if missing_names:
                raise ValueError(
                    "Configuration OIDC incomplète : " + ", ".join(missing_names)
                )
            if len(self.session_secret) < 32:
                raise ValueError("YOTO_SESSION_SECRET doit contenir au moins 32 caractères")
            if not self.public_base_url.startswith("https://"):
                if not local_url:
                    raise ValueError("OIDC actif : YOTO_PUBLIC_BASE_URL doit utiliser HTTPS")
            issuer_host = self.oidc_issuer_url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
            if not self.oidc_issuer_url.startswith("https://") and issuer_host not in {
                "localhost",
                "127.0.0.1",
                "[::1]",
            }:
                raise ValueError("YOTO_OIDC_ISSUER_URL doit utiliser HTTPS")
            if "*" in self.cors_origins:
                raise ValueError("YOTO_CORS_ORIGINS ne peut pas contenir * avec OIDC actif")
        return self

    def cors_origin_list(self) -> list[str]:
        configured = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        if configured:
            return configured
        return [self.public_base_url.rstrip("/")] if self.public_base_url.startswith(("http://", "https://")) else []


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
