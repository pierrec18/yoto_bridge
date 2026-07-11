"""Jeton partagé protégeant les URLs de streaming (§14).

Le token est intégré dans l'URL déposée côté Yoto (`?t=...`). Il peut être
réinitialisé : les anciennes URLs deviennent alors invalides.
"""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Settings
from .secrets import decrypt, encrypt


def new_stream_token() -> str:
    return secrets.token_urlsafe(24)


async def get_or_create_settings(session: AsyncSession) -> Settings:
    """Renvoie la ligne de réglages (id=1), en garantissant un token de stream."""
    settings = await session.get(Settings, 1)
    if settings is None:
        settings = Settings(id=1, stream_token=encrypt(new_stream_token()))
        session.add(settings)
    elif not settings.stream_token:
        settings.stream_token = encrypt(new_stream_token())
    return settings


def token_is_valid(settings: Settings, provided: str | None) -> bool:
    stored = decrypt(settings.stream_token)
    if not stored or not provided:
        return False
    return secrets.compare_digest(stored, provided)
