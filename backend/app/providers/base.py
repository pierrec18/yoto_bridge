"""Abstraction de la source musicale.

Toute l'application dépend uniquement de cette interface, jamais d'une
implémentation concrète (Navidrome, Plex, Jellyfin...). Voir §16 du cahier
des charges.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass(slots=True)
class ProviderTrack:
    """Un morceau tel qu'exposé par une source musicale."""

    id: str
    title: str
    artist: str | None = None
    album: str | None = None
    album_id: str | None = None
    artist_id: str | None = None
    genre: str | None = None
    year: int | None = None
    duration: int | None = None  # secondes
    rating: int | None = None  # 1..5
    cover_art: str | None = None
    track_number: int | None = None
    disc_number: int | None = None


@dataclass(slots=True)
class ProviderAlbum:
    id: str
    name: str
    artist: str | None = None
    artist_id: str | None = None
    year: int | None = None
    genre: str | None = None
    song_count: int | None = None
    cover_art: str | None = None


@dataclass(slots=True)
class ProviderPlaylist:
    id: str
    name: str
    song_count: int | None = None
    duration: int | None = None
    cover_art: str | None = None


@dataclass(slots=True)
class ProviderArtist:
    id: str
    name: str
    album_count: int | None = None
    cover_art: str | None = None


@dataclass(slots=True)
class StreamResponse:
    """Flux audio proxifié depuis la source, prêt à être renvoyé à la Yoto."""

    content_type: str
    status_code: int
    body: AsyncIterator[bytes]
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SearchFilters:
    """Filtres du mode Recherche (§5)."""

    query: str | None = None
    genre: str | None = None
    min_rating: int | None = None
    min_year: int | None = None
    max_year: int | None = None


class MusicProvider(ABC):
    """Interface commune à toutes les sources musicales."""

    @abstractmethod
    async def ping(self) -> bool:
        """Vérifie que la source est joignable et les identifiants valides."""

    @abstractmethod
    async def get_playlists(self) -> list[ProviderPlaylist]: ...

    @abstractmethod
    async def get_playlist_tracks(self, playlist_id: str) -> list[ProviderTrack]: ...

    @abstractmethod
    async def get_albums(self) -> list[ProviderAlbum]: ...

    @abstractmethod
    async def get_album_tracks(self, album_id: str) -> list[ProviderTrack]: ...

    @abstractmethod
    async def get_artists(self) -> list[ProviderArtist]: ...

    @abstractmethod
    async def get_genres(self) -> list[str]: ...

    @abstractmethod
    async def get_track(self, track_id: str) -> ProviderTrack | None: ...

    @abstractmethod
    async def search(self, filters: SearchFilters, limit: int = 100) -> list[ProviderTrack]: ...

    @abstractmethod
    async def get_cover_art(self, cover_id: str, *, size: int = 300) -> StreamResponse: ...

    @abstractmethod
    async def stream(
        self,
        track_id: str,
        *,
        fmt: str = "mp3",
        max_bitrate: int = 192,
        range_header: str | None = None,
    ) -> StreamResponse:
        """Ouvre un flux transcodé pour un morceau. L'appelant doit consommer
        puis fermer le corps de la réponse."""

    async def close(self) -> None:  # pragma: no cover - override optionnel
        """Libère les ressources (connexions HTTP)."""
