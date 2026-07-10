"""Provider factice pour les tests de résolution."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.providers.base import (
    MusicProvider,
    ProviderAlbum,
    ProviderArtist,
    ProviderPlaylist,
    ProviderTrack,
    SearchFilters,
    StreamResponse,
)


class FakeProvider(MusicProvider):
    def __init__(
        self,
        *,
        tracks: dict[str, ProviderTrack] | None = None,
        playlists: dict[str, list[ProviderTrack]] | None = None,
        albums: dict[str, list[ProviderTrack]] | None = None,
    ) -> None:
        self.tracks = tracks or {}
        self.playlists = playlists or {}
        self.albums = albums or {}
        self.closed = False

    async def ping(self) -> bool:
        return True

    async def get_playlists(self) -> list[ProviderPlaylist]:
        return [ProviderPlaylist(id=k, name=k) for k in self.playlists]

    async def get_playlist_tracks(self, playlist_id: str) -> list[ProviderTrack]:
        return list(self.playlists.get(playlist_id, []))

    async def get_albums(self) -> list[ProviderAlbum]:
        return [ProviderAlbum(id=k, name=k) for k in self.albums]

    async def get_album_tracks(self, album_id: str) -> list[ProviderTrack]:
        return list(self.albums.get(album_id, []))

    async def get_artists(self) -> list[ProviderArtist]:
        return []

    async def get_genres(self) -> list[str]:
        return []

    async def get_track(self, track_id: str) -> ProviderTrack | None:
        return self.tracks.get(track_id)

    async def search(self, filters: SearchFilters, limit: int = 100) -> list[ProviderTrack]:
        return list(self.tracks.values())

    async def get_cover_art(self, cover_id: str, *, size: int = 300) -> StreamResponse:
        async def body() -> AsyncIterator[bytes]:
            yield b"fake-image"

        return StreamResponse(content_type="image/jpeg", status_code=200, body=body())

    async def stream(
        self,
        track_id: str,
        *,
        fmt: str = "mp3",
        max_bitrate: int = 192,
        range_header: str | None = None,
    ) -> StreamResponse:
        async def body() -> AsyncIterator[bytes]:
            yield b"\x00\x01"

        return StreamResponse(content_type="audio/mpeg", status_code=200, body=body())

    async def close(self) -> None:
        self.closed = True
