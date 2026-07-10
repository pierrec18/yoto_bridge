"""Construction d'un `MusicProvider` à partir des réglages en base."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Settings
from .base import MusicProvider
from .subsonic import SubsonicProvider


class ProviderNotConfigured(RuntimeError):
    """Aucune source musicale n'est configurée."""


_BUILDERS = {
    "navidrome": lambda s: SubsonicProvider(s.navidrome_url, s.username, s.password),
}


async def get_settings(session: AsyncSession) -> Settings | None:
    return await session.get(Settings, 1)


def build_provider(settings: Settings) -> MusicProvider:
    if not settings.navidrome_url or not settings.username or not settings.password:
        raise ProviderNotConfigured("Source musicale non configurée")
    builder = _BUILDERS.get(settings.provider)
    if builder is None:
        raise ProviderNotConfigured(f"Fournisseur inconnu : {settings.provider}")
    return builder(settings)


async def provider_from_session(session: AsyncSession) -> MusicProvider:
    settings = await get_settings(session)
    if settings is None:
        raise ProviderNotConfigured("Source musicale non configurée")
    return build_provider(settings)
