"""Synchronisation de la bibliothèque source vers le cache SQLite (§2)."""

from __future__ import annotations

import logging

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    LibraryAlbum,
    LibraryArtist,
    LibraryPlaylist,
    LibraryTrack,
)
from ..providers.base import MusicProvider
from ..schemas import SyncResult

logger = logging.getLogger(__name__)


class LibrarySyncService:
    def __init__(self, session: AsyncSession, provider: MusicProvider) -> None:
        self._session = session
        self._provider = provider

    async def sync(self) -> SyncResult:
        """Recharge intégralement le cache. Idempotent (remplace tout)."""
        albums = await self._provider.get_albums()
        playlists = await self._provider.get_playlists()
        artists = await self._provider.get_artists()

        # Les morceaux sont récupérés album par album (pas d'endpoint « tout »
        # standard en Subsonic).
        tracks_seen: dict[str, LibraryTrack] = {}
        for album in albums:
            for t in await self._provider.get_album_tracks(album.id):
                tracks_seen[t.id] = LibraryTrack(
                    id=t.id,
                    title=t.title,
                    artist=t.artist,
                    album=t.album,
                    album_id=t.album_id,
                    genre=t.genre,
                    year=t.year,
                    duration=t.duration,
                    rating=t.rating,
                    cover_art=t.cover_art or album.cover_art,
                    track_number=t.track_number,
                    disc_number=t.disc_number,
                )

        await self._replace(LibraryTrack, tracks_seen.values())
        await self._replace(
            LibraryAlbum,
            [
                LibraryAlbum(
                    id=a.id,
                    name=a.name,
                    artist=a.artist,
                    artist_id=a.artist_id,
                    year=a.year,
                    genre=a.genre,
                    song_count=a.song_count,
                    cover_art=a.cover_art,
                )
                for a in albums
            ],
        )
        await self._replace(
            LibraryPlaylist,
            [
                LibraryPlaylist(
                    id=p.id, name=p.name, song_count=p.song_count, duration=p.duration
                )
                for p in playlists
            ],
        )
        await self._replace(
            LibraryArtist,
            [
                LibraryArtist(id=a.id, name=a.name, album_count=a.album_count)
                for a in artists
            ],
        )

        genres = await self._provider.get_genres()
        await self._session.commit()

        result = SyncResult(
            tracks=len(tracks_seen),
            albums=len(albums),
            playlists=len(playlists),
            artists=len(artists),
            genres=len(genres),
        )
        logger.info("Synchronisation terminée : %s", result.model_dump())
        return result

    async def _replace(self, model: type, rows) -> None:
        await self._session.execute(delete(model))
        self._session.add_all(list(rows))
