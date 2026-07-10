"""Publication d'une carte vers l'API Yoto : mélange stream + hors ligne (§18)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_config
from ..models import Card, CardTrack, Delivery, PlaybackMode, Settings, YotoIcon, YotoMedia
from ..providers.base import MusicProvider
from ..yoto.client import YotoClient, YotoError

logger = logging.getLogger(__name__)


class PublishError(RuntimeError):
    """Publication impossible (configuration invalide)."""


class PublishService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        yoto: YotoClient,
        provider: MusicProvider,
    ) -> None:
        self._session = session
        self._settings = settings
        self._yoto = yoto
        self._provider = provider

    async def publish(self, card: Card) -> dict[str, Any]:
        self._validate(card)
        chapters: list[dict[str, Any]] = []
        total_duration = 0
        total_size = 0

        for track in sorted(card.tracks, key=lambda t: t.track_number):
            key = f"{track.track_number:02d}"
            try:
                display = await self._display_for_track(track)
            except Exception:  # une pochette ne doit jamais bloquer l'audio
                logger.warning(
                    "Impossible de créer l'icône de la piste %s", track.track_number, exc_info=True
                )
                display = None
            if track.delivery == Delivery.OFFLINE:
                track_obj, dur, size = await self._offline_track(track, key)
                total_duration += dur
                total_size += size
            else:
                track_obj = self._stream_track(card, track, key)
            if display:
                track_obj["display"] = display
            chapter = {
                "key": key,
                "title": track.label or f"Piste {track.track_number}",
                "overlayLabel": str(track.track_number),
                "tracks": [track_obj],
            }
            if display:
                chapter["display"] = display
            chapters.append(chapter)

        body: dict[str, Any] = {
            "title": card.name,
            "content": {
                "chapters": chapters,
                "config": {"resumeTimeout": 2592000},
                "playbackType": "linear",
            },
            "metadata": {
                "description": card.description or "",
                "media": {"duration": total_duration, "fileSize": total_size},
            },
        }
        if card.yoto_card_id:
            body["cardId"] = card.yoto_card_id

        result = await self._yoto.create_or_update_content(body)
        card_id = result.get("cardId") or result.get("card", {}).get("cardId")
        if card_id:
            card.yoto_card_id = card_id
        logger.info("Carte %s publiée sur Yoto (cardId=%s)", card.id, card.yoto_card_id)
        return {"yoto_card_id": card.yoto_card_id, "chapters": len(chapters)}

    async def _display_for_track(self, track: CardTrack) -> dict[str, str] | None:
        """Convertit la pochette de la source en icône Yoto et la met en cache."""
        cover_art = str(track.config.get("cover_art") or "") or await self._find_cover_art(track)
        if not cover_art:
            return None
        cached = await self._session.get(YotoIcon, cover_art)
        if cached is not None:
            return {"icon16x16": f"yoto:#{cached.media_id}"}

        response = await self._provider.get_cover_art(cover_art, size=300)
        if response.status_code >= 400:
            async for _ in response.body:
                pass
            return None
        data = b"".join([chunk async for chunk in response.body])
        if not data:
            return None
        media_id = await self._yoto.upload_icon(
            data,
            response.content_type,
            filename=f"album-{cover_art}",
        )
        self._session.add(YotoIcon(cover_art=cover_art, media_id=media_id))
        return {"icon16x16": f"yoto:#{media_id}"}

    async def _find_cover_art(self, track: CardTrack) -> str | None:
        if track.mode == PlaybackMode.FIXED and track.config.get("song_id"):
            song = await self._provider.get_track(str(track.config["song_id"]))
            return song.cover_art if song else None
        if track.mode == PlaybackMode.ALBUM and track.config.get("album_id"):
            songs = await self._provider.get_album_tracks(str(track.config["album_id"]))
            return songs[0].cover_art if songs else None
        if track.mode == PlaybackMode.PLAYLIST and track.config.get("playlist_id"):
            songs = await self._provider.get_playlist_tracks(str(track.config["playlist_id"]))
            return songs[0].cover_art if songs else None
        return None

    # -- Validation -------------------------------------------------------

    def _validate(self, card: Card) -> None:
        if not card.tracks:
            raise PublishError("La carte n'a aucune piste")
        for track in card.tracks:
            if track.delivery == Delivery.OFFLINE and (
                track.mode != PlaybackMode.FIXED or not track.config.get("song_id")
            ):
                raise PublishError(
                    f"Piste {track.track_number} : le mode hors ligne exige un morceau fixe"
                )
        if not self._settings.stream_token and any(
            t.delivery == Delivery.STREAM for t in card.tracks
        ):
            raise PublishError("Token de streaming manquant")

    # -- Construction des pistes -----------------------------------------

    def _stream_track(self, card: Card, track: CardTrack, key: str) -> dict[str, Any]:
        base = get_config().public_base_url.rstrip("/")
        url = f"{base}/stream/{card.id}/{track.track_number}?t={self._settings.stream_token}"
        return {
            "key": key,
            "title": track.label or f"Piste {track.track_number}",
            "trackUrl": url,
            "type": "stream",
            "format": get_config().stream_format,
            "overlayLabel": str(track.track_number),
        }

    async def _offline_track(
        self, track: CardTrack, key: str
    ) -> tuple[dict[str, Any], int, int]:
        song_id = str(track.config["song_id"])
        media = await self._ensure_media(song_id)
        track_obj = {
            "key": key,
            "title": track.label or media.title or f"Piste {track.track_number}",
            "trackUrl": f"yoto:#{media.sha256}",
            "type": "audio",
            "format": media.format or "mp3",
            "duration": media.duration,
            "fileSize": media.file_size,
            "channels": media.channels,
            "overlayLabel": str(track.track_number),
        }
        return track_obj, media.duration or 0, media.file_size or 0

    async def _ensure_media(self, song_id: str) -> YotoMedia:
        """Récupère (ou upload) le fichier transcodé Yoto pour ce morceau."""
        cached = await self._session.get(YotoMedia, song_id)
        if cached is not None:
            return cached

        # 1. Récupérer le MP3 depuis Navidrome (transcodage délégué).
        stream = await self._provider.stream(
            song_id,
            fmt=get_config().stream_format,
            max_bitrate=get_config().stream_default_bitrate,
        )
        chunks = [c async for c in stream.body]
        data = b"".join(chunks)
        if not data:
            raise PublishError(f"Morceau vide côté source : {song_id}")

        # 2. Upload + transcodage Yoto.
        upload_url, upload_id = await self._yoto.get_upload_url()
        await self._yoto.upload_bytes(upload_url, data, "audio/mpeg")
        try:
            transcode = await self._yoto.poll_transcoded(upload_id)
        except YotoError as exc:
            raise PublishError(str(exc)) from exc

        info = transcode.get("transcodedInfo", {})
        media = YotoMedia(
            song_id=song_id,
            sha256=transcode["transcodedSha256"],
            title=info.get("metadata", {}).get("title"),
            duration=info.get("duration"),
            file_size=info.get("fileSize"),
            channels=info.get("channels"),
            format=info.get("format"),
        )
        self._session.add(media)
        return media
