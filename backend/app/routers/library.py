"""Accès à la bibliothèque en cache (§8, §10)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import LibraryAlbum, LibraryArtist, LibraryPlaylist, LibraryTrack
from ..providers.factory import ProviderNotConfigured, provider_from_session
from ..schemas import AlbumOut, ArtistOut, PlaylistOut, TrackOut

router = APIRouter(prefix="/api/library", tags=["library"])


def _cover_url(cover_art: str | None) -> str | None:
    return f"/api/library/cover?id={quote(cover_art)}" if cover_art else None


def _track_out(track: LibraryTrack) -> TrackOut:
    return TrackOut(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        genre=track.genre,
        year=track.year,
        duration=track.duration,
        cover_art=track.cover_art,
        cover_url=_cover_url(track.cover_art),
        track_number=track.track_number,
        disc_number=track.disc_number,
    )


def _album_out(album: LibraryAlbum) -> AlbumOut:
    return AlbumOut(
        id=album.id,
        name=album.name,
        artist=album.artist,
        year=album.year,
        cover_art=album.cover_art,
        cover_url=_cover_url(album.cover_art),
    )


@router.get("/search", response_model=list[TrackOut])
async def search(
    q: str = Query(default="", description="Recherche instantanée sur titre/artiste/album"),
    genre: str | None = None,
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[TrackOut]:
    stmt = select(LibraryTrack)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                LibraryTrack.title.ilike(like),
                LibraryTrack.artist.ilike(like),
                LibraryTrack.album.ilike(like),
            )
        )
    if genre:
        stmt = stmt.where(LibraryTrack.genre == genre)
    stmt = stmt.order_by(LibraryTrack.title).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_track_out(row) for row in rows]


@router.get("/playlists", response_model=list[PlaylistOut])
async def playlists(session: AsyncSession = Depends(get_session)) -> list[PlaylistOut]:
    rows = (await session.execute(select(LibraryPlaylist))).scalars().all()
    return [PlaylistOut(id=r.id, name=r.name, song_count=r.song_count) for r in rows]


@router.get("/albums", response_model=list[AlbumOut])
async def albums(
    q: str = "", limit: int = Query(default=1000, le=2000),
    session: AsyncSession = Depends(get_session),
) -> list[AlbumOut]:
    stmt = select(LibraryAlbum)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(LibraryAlbum.name.ilike(like), LibraryAlbum.artist.ilike(like)))
    rows = (
        await session.execute(stmt.order_by(LibraryAlbum.name).limit(limit))
    ).scalars().all()
    return [_album_out(row) for row in rows]


@router.get("/albums/{album_id}/tracks", response_model=list[TrackOut])
async def album_tracks(
    album_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[TrackOut]:
    rows = (
        await session.execute(
            select(LibraryTrack)
            .where(LibraryTrack.album_id == album_id)
            .order_by(
                LibraryTrack.disc_number,
                LibraryTrack.track_number,
                LibraryTrack.title,
            )
        )
    ).scalars().all()
    return [_track_out(row) for row in rows]


@router.get("/cover")
async def cover(
    id: str = Query(min_length=1),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    try:
        provider = await provider_from_session(session)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response = await provider.get_cover_art(id, size=300)
    if response.status_code >= 400:
        await provider.close()
        raise HTTPException(status_code=response.status_code, detail="Pochette introuvable")

    async def body():
        try:
            async for chunk in response.body:
                yield chunk
        finally:
            await provider.close()

    return StreamingResponse(
        body(),
        media_type=response.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/artists", response_model=list[ArtistOut])
async def artists(
    q: str = "",
    limit: int = Query(default=200, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[ArtistOut]:
    stmt = select(LibraryArtist)
    if q:
        stmt = stmt.where(LibraryArtist.name.ilike(f"%{q}%"))
    rows = (
        await session.execute(stmt.order_by(LibraryArtist.name).limit(limit))
    ).scalars().all()
    return [ArtistOut(id=r.id, name=r.name, album_count=r.album_count) for r in rows]


@router.get("/artists/{artist_id}/albums", response_model=list[AlbumOut])
async def artist_albums(
    artist_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[AlbumOut]:
    rows = (
        await session.execute(
            select(LibraryAlbum)
            .where(LibraryAlbum.artist_id == artist_id)
            .order_by(LibraryAlbum.name)
        )
    ).scalars().all()
    return [_album_out(row) for row in rows]


@router.get("/genres", response_model=list[str])
async def genres(session: AsyncSession = Depends(get_session)) -> list[str]:
    stmt = select(distinct(LibraryTrack.genre)).where(LibraryTrack.genre.is_not(None))
    return [g for g in (await session.execute(stmt)).scalars().all() if g]
