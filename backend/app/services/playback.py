"""Résolution d'une piste Yoto vers un morceau concret (§4, §5, §6).

Le point délicat : la Yoto peut ré-interroger la même URL plusieurs fois pour
une seule lecture (requêtes `Range` pour le seek, reprises réseau). On ne doit
donc pas choisir un nouveau morceau à chaque requête HTTP. Un petit cache TTL
par (carte, piste) garantit qu'une même piste renvoie le même morceau pendant
une courte fenêtre ; passé ce délai, une nouvelle requête fait avancer la
progression (playlist/album) ou tire un nouveau morceau (random/smart/search).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_config
from ..models import CardTrack, HistoryEntry, LibraryTrack, PlaybackMode
from ..providers.base import MusicProvider, ProviderTrack, SearchFilters


class ResolutionError(RuntimeError):
    """Impossible de déterminer un morceau pour cette piste."""


@dataclass
class _CachedResolution:
    track: ProviderTrack
    expires_at: float


# Cache mémoire process : (card_id, track_number) -> résolution récente.
_cache: dict[tuple[int, int], _CachedResolution] = {}


def _cache_get(key: tuple[int, int]) -> ProviderTrack | None:
    entry = _cache.get(key)
    if entry and entry.expires_at > time.monotonic():
        return entry.track
    _cache.pop(key, None)
    return None


def _cache_put(key: tuple[int, int], track: ProviderTrack, ttl: float) -> None:
    _cache[key] = _CachedResolution(track=track, expires_at=time.monotonic() + ttl)


class PlaybackService:
    def __init__(self, session: AsyncSession, provider: MusicProvider) -> None:
        self._session = session
        self._provider = provider

    async def resolve(
        self, card_track: CardTrack, *, ip: str | None = None
    ) -> ProviderTrack:
        """Renvoie le morceau à jouer pour cette piste et journalise l'écoute."""
        key = (card_track.card_id, card_track.track_number)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        track = await self._choose(card_track)
        card_track.last_song_id = track.id
        await self._log_history(card_track, track, ip)
        _cache_put(key, track, get_config().resolution_ttl_seconds)
        return track

    # -- Sélection selon le mode -----------------------------------------

    async def _choose(self, ct: CardTrack) -> ProviderTrack:
        mode = ct.mode
        if mode == PlaybackMode.FIXED:
            return await self._fixed(ct)
        if mode == PlaybackMode.PLAYLIST:
            return await self._sequential(ct, playlist=True)
        if mode == PlaybackMode.ALBUM:
            return await self._sequential(ct, playlist=False)
        if mode == PlaybackMode.RANDOM:
            return await self._random(ct)
        if mode == PlaybackMode.SMART:
            return await self._smart(ct)
        if mode == PlaybackMode.SEARCH:
            return await self._search(ct)
        raise ResolutionError(f"Mode inconnu : {mode}")

    async def _fixed(self, ct: CardTrack) -> ProviderTrack:
        song_id = ct.config.get("song_id")
        if not song_id:
            raise ResolutionError("Mode fixe sans song_id")
        track = await self._provider.get_track(str(song_id))
        if track is None:
            raise ResolutionError(f"Morceau introuvable : {song_id}")
        return track

    async def _sequential(self, ct: CardTrack, *, playlist: bool) -> ProviderTrack:
        if playlist:
            source_id = ct.config.get("playlist_id")
            if not source_id:
                raise ResolutionError("Mode playlist sans playlist_id")
            tracks = await self._provider.get_playlist_tracks(str(source_id))
        else:
            source_id = ct.config.get("album_id")
            if not source_id:
                raise ResolutionError("Mode album sans album_id")
            tracks = await self._provider.get_album_tracks(str(source_id))
        if not tracks:
            raise ResolutionError("Source séquentielle vide")
        index = ct.position % len(tracks)
        ct.position = (index + 1) % len(tracks)
        return tracks[index]

    async def _random(self, ct: CardTrack) -> ProviderTrack:
        track = await self._random_library_track(exclude_ids={ct.last_song_id})
        if track is None:
            raise ResolutionError("Bibliothèque vide (lancer une synchro ?)")
        return track

    async def _smart(self, ct: CardTrack) -> ProviderTrack:
        last_artist: str | None = None
        last_album: str | None = None
        if ct.last_song_id:
            last = await self._session.get(LibraryTrack, ct.last_song_id)
            if last is not None:
                last_artist, last_album = last.artist, last.album
        track = await self._random_library_track(
            exclude_ids={ct.last_song_id},
            exclude_artist=last_artist,
            exclude_album=last_album,
        )
        if track is None:  # bibliothèque trop petite pour respecter les contraintes
            track = await self._random_library_track(exclude_ids={ct.last_song_id})
        if track is None:
            raise ResolutionError("Bibliothèque vide (lancer une synchro ?)")
        return track

    async def _search(self, ct: CardTrack) -> ProviderTrack:
        filters = SearchFilters(
            query=ct.config.get("query"),
            genre=ct.config.get("genre"),
            min_rating=ct.config.get("min_rating"),
            min_year=ct.config.get("min_year"),
            max_year=ct.config.get("max_year"),
        )
        results = await self._provider.search(filters, limit=200)
        candidates = [t for t in results if t.id != ct.last_song_id] or results
        if not candidates:
            raise ResolutionError("Aucun morceau ne correspond à la recherche")
        return random.choice(candidates)

    # -- Helpers ----------------------------------------------------------

    async def _random_library_track(
        self,
        *,
        exclude_ids: set[str | None] | None = None,
        exclude_artist: str | None = None,
        exclude_album: str | None = None,
    ) -> ProviderTrack | None:
        stmt = select(LibraryTrack)
        excluded = {i for i in (exclude_ids or set()) if i}
        if excluded:
            stmt = stmt.where(LibraryTrack.id.notin_(excluded))
        if exclude_artist:
            stmt = stmt.where(LibraryTrack.artist != exclude_artist)
        if exclude_album:
            stmt = stmt.where(LibraryTrack.album != exclude_album)
        stmt = stmt.order_by(func.random()).limit(1)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return ProviderTrack(
            id=row.id,
            title=row.title,
            artist=row.artist,
            album=row.album,
            album_id=row.album_id,
            genre=row.genre,
            year=row.year,
            duration=row.duration,
            rating=row.rating,
        )

    async def _log_history(
        self, ct: CardTrack, track: ProviderTrack, ip: str | None
    ) -> None:
        self._session.add(
            HistoryEntry(
                card_id=ct.card_id,
                track_number=ct.track_number,
                song_id=track.id,
                song_title=track.title,
                artist=track.artist,
                album=track.album,
                duration=track.duration,
                ip_address=ip,
            )
        )


def clear_resolution_cache() -> None:
    """Utilisé par les tests et lors d'un changement de configuration."""
    _cache.clear()
