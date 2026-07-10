"""Implémentation `MusicProvider` pour l'API Subsonic (Navidrome).

Le transcodage FLAC -> MP3 est délégué à Navidrome via `stream.view`. Aucun
décodage audio n'est effectué localement (§ Fonctionnement général).
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import (
    MusicProvider,
    ProviderAlbum,
    ProviderArtist,
    ProviderPlaylist,
    ProviderTrack,
    SearchFilters,
    StreamResponse,
)

_API_VERSION = "1.16.1"
_CLIENT_NAME = "yoto-bridge"


class SubsonicError(RuntimeError):
    """Erreur renvoyée par le serveur Subsonic."""


class SubsonicProvider(MusicProvider):
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._client = client or httpx.AsyncClient(timeout=timeout)

    # -- Authentification -------------------------------------------------

    def _auth_params(self) -> dict[str, str]:
        salt = secrets.token_hex(8)
        token = hashlib.md5(f"{self._password}{salt}".encode()).hexdigest()
        return {
            "u": self._username,
            "t": token,
            "s": salt,
            "v": _API_VERSION,
            "c": _CLIENT_NAME,
            "f": "json",
        }

    def _url(self, endpoint: str) -> str:
        return f"{self._base_url}/rest/{endpoint}"

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = self._auth_params()
        if params:
            merged.update({k: v for k, v in params.items() if v is not None})
        resp = await self._client.get(self._url(endpoint), params=merged)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json().get("subsonic-response", {})
        if payload.get("status") != "ok":
            error = payload.get("error", {})
            raise SubsonicError(error.get("message", "Erreur Subsonic inconnue"))
        return payload

    # -- Mapping ----------------------------------------------------------

    @staticmethod
    def _to_track(raw: dict[str, Any]) -> ProviderTrack:
        return ProviderTrack(
            id=str(raw["id"]),
            title=raw.get("title", "?"),
            artist=raw.get("artist"),
            album=raw.get("album"),
            album_id=str(raw["albumId"]) if raw.get("albumId") is not None else None,
            artist_id=str(raw["artistId"]) if raw.get("artistId") is not None else None,
            genre=raw.get("genre"),
            year=raw.get("year"),
            duration=raw.get("duration"),
            rating=raw.get("userRating"),
            cover_art=str(raw["coverArt"]) if raw.get("coverArt") is not None else None,
        )

    # -- Interface --------------------------------------------------------

    async def ping(self) -> bool:
        await self._get("ping.view")
        return True

    async def get_playlists(self) -> list[ProviderPlaylist]:
        data = await self._get("getPlaylists.view")
        items = data.get("playlists", {}).get("playlist", [])
        return [
            ProviderPlaylist(
                id=str(p["id"]),
                name=p.get("name", "?"),
                song_count=p.get("songCount"),
                duration=p.get("duration"),
                cover_art=str(p["coverArt"]) if p.get("coverArt") is not None else None,
            )
            for p in items
        ]

    async def get_playlist_tracks(self, playlist_id: str) -> list[ProviderTrack]:
        data = await self._get("getPlaylist.view", {"id": playlist_id})
        entries = data.get("playlist", {}).get("entry", [])
        return [self._to_track(e) for e in entries]

    async def get_albums(self) -> list[ProviderAlbum]:
        albums: list[ProviderAlbum] = []
        offset = 0
        page_size = 500
        while True:
            data = await self._get(
                "getAlbumList2.view",
                {"type": "alphabeticalByName", "size": page_size, "offset": offset},
            )
            page = data.get("albumList2", {}).get("album", [])
            if not page:
                break
            albums.extend(
                ProviderAlbum(
                    id=str(a["id"]),
                    name=a.get("name", "?"),
                    artist=a.get("artist"),
                    artist_id=str(a["artistId"]) if a.get("artistId") is not None else None,
                    year=a.get("year"),
                    genre=a.get("genre"),
                    song_count=a.get("songCount"),
                    cover_art=str(a["coverArt"]) if a.get("coverArt") is not None else None,
                )
                for a in page
            )
            if len(page) < page_size:
                break
            offset += page_size
        return albums

    async def get_album_tracks(self, album_id: str) -> list[ProviderTrack]:
        data = await self._get("getAlbum.view", {"id": album_id})
        songs = data.get("album", {}).get("song", [])
        return [self._to_track(s) for s in songs]

    async def get_artists(self) -> list[ProviderArtist]:
        data = await self._get("getArtists.view")
        artists: list[ProviderArtist] = []
        for index in data.get("artists", {}).get("index", []):
            for a in index.get("artist", []):
                artists.append(
                    ProviderArtist(
                        id=str(a["id"]),
                        name=a.get("name", "?"),
                        album_count=a.get("albumCount"),
                        cover_art=str(a["coverArt"]) if a.get("coverArt") is not None else None,
                    )
                )
        return artists

    async def get_genres(self) -> list[str]:
        data = await self._get("getGenres.view")
        genres = data.get("genres", {}).get("genre", [])
        return [g["value"] for g in genres if g.get("value")]

    async def get_track(self, track_id: str) -> ProviderTrack | None:
        try:
            data = await self._get("getSong.view", {"id": track_id})
        except SubsonicError:
            return None
        song = data.get("song")
        return self._to_track(song) if song else None

    async def search(self, filters: SearchFilters, limit: int = 100) -> list[ProviderTrack]:
        data = await self._get(
            "search3.view",
            {
                "query": filters.query or "",
                "songCount": limit,
                "albumCount": 0,
                "artistCount": 0,
            },
        )
        songs = data.get("searchResult3", {}).get("song", [])
        tracks = [self._to_track(s) for s in songs]
        return [t for t in tracks if _matches(t, filters)]

    async def get_cover_art(self, cover_id: str, *, size: int = 300) -> StreamResponse:
        params = self._auth_params()
        params.update({"id": cover_id, "size": str(size)})
        request = self._client.build_request("GET", self._url("getCoverArt.view"), params=params)
        response = await self._client.send(request, stream=True)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()

        return StreamResponse(
            content_type=response.headers.get("content-type", "image/jpeg"),
            status_code=response.status_code,
            body=body(),
            headers={
                "cache-control": response.headers.get("cache-control", "public, max-age=86400")
            },
        )

    async def stream(
        self,
        track_id: str,
        *,
        fmt: str = "mp3",
        max_bitrate: int = 192,
        range_header: str | None = None,
    ) -> StreamResponse:
        params = self._auth_params()
        params.update({"id": track_id, "format": fmt, "maxBitRate": str(max_bitrate)})
        headers = {"Range": range_header} if range_header else {}
        request = self._client.build_request(
            "GET", self._url("stream.view"), params=params, headers=headers
        )
        response = await self._client.send(request, stream=True)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()

        forwarded = {
            k: v
            for k, v in response.headers.items()
            if k.lower() in {"content-length", "content-range", "accept-ranges"}
        }
        return StreamResponse(
            content_type=response.headers.get("content-type", "audio/mpeg"),
            status_code=response.status_code,
            body=body(),
            headers=forwarded,
        )

    async def close(self) -> None:
        await self._client.aclose()


def _matches(track: ProviderTrack, filters: SearchFilters) -> bool:
    """Applique les filtres non gérés nativement par search3 (rating, année)."""
    if filters.genre and (track.genre or "").lower() != filters.genre.lower():
        return False
    if filters.min_rating is not None and (track.rating or 0) < filters.min_rating:
        return False
    if filters.min_year is not None and (track.year or 0) < filters.min_year:
        return False
    if filters.max_year is not None and (track.year or 9999) > filters.max_year:
        return False
    return True
