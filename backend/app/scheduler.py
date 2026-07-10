"""Synchronisation périodique de la bibliothèque (§2)."""

from __future__ import annotations

import asyncio
import logging

from .config import get_config
from .database import SessionLocal
from .providers.factory import ProviderNotConfigured, provider_from_session
from .services.library import LibrarySyncService

logger = logging.getLogger(__name__)


async def _run_once() -> None:
    async with SessionLocal() as session:
        try:
            provider = await provider_from_session(session)
        except ProviderNotConfigured:
            logger.info("Sync ignorée : source non configurée")
            return
        try:
            await LibrarySyncService(session, provider).sync()
        finally:
            await provider.close()


async def periodic_sync() -> None:
    """Boucle de fond : sync au démarrage puis toutes les heures."""
    interval = get_config().sync_interval_seconds
    while True:
        try:
            await _run_once()
        except Exception:  # noqa: BLE001 - une erreur ne doit pas tuer la boucle
            logger.exception("Échec de la synchronisation périodique")
        await asyncio.sleep(interval)
