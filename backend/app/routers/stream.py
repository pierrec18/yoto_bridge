"""Proxy de streaming pour la Yoto (§7, §14).

C'est l'URL que chaque piste de la carte MYO cible. La Yoto (ou son backend)
appelle `GET /stream/{card_id}/{track_number}` ; le serveur choisit le morceau
puis proxifie le flux MP3 transcodé par Navidrome. L'URL Navidrome et les
identifiants ne sont jamais exposés.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_config
from ..database import get_session
from ..models import CardTrack, Settings
from ..providers.factory import ProviderNotConfigured, build_provider
from ..security import token_is_valid
from ..services.playback import PlaybackService, ResolutionError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/{card_id}/{track_number}")
async def stream_track(
    card_id: int,
    track_number: int,
    request: Request,
    t: str | None = None,
    range_header: str | None = Header(default=None, alias="Range"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    # Jeton partagé exigé (déposé côté Yoto dans l'URL) : ?t=...
    settings = await session.get(Settings, 1)
    if settings is None or not token_is_valid(settings, t):
        raise HTTPException(status_code=403, detail="Jeton invalide")

    card_track = (
        await session.execute(
            select(CardTrack).where(
                CardTrack.card_id == card_id,
                CardTrack.track_number == track_number,
            )
        )
    ).scalar_one_or_none()
    if card_track is None:
        raise HTTPException(status_code=404, detail="Piste inconnue")

    try:
        provider = build_provider(settings)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    config = get_config()
    try:
        service = PlaybackService(session, provider)
        chosen = await service.resolve(card_track, ip=request.client.host if request.client else None)
        # On persiste progression + historique AVANT de commencer à streamer.
        await session.commit()

        stream = await provider.stream(
            chosen.id,
            fmt=config.stream_format,
            max_bitrate=config.stream_default_bitrate,
            range_header=range_header,
        )
    except ResolutionError as exc:
        await provider.close()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        await provider.close()
        raise

    logger.info(
        "Stream carte=%s piste=%s -> %s (%s)",
        card_id,
        track_number,
        chosen.title,
        chosen.id,
    )

    async def piped() -> AsyncIterator[bytes]:
        try:
            async for chunk in stream.body:
                yield chunk
        finally:
            await provider.close()

    return StreamingResponse(
        piped(),
        status_code=stream.status_code,
        media_type=stream.content_type,
        headers=stream.headers,
    )
