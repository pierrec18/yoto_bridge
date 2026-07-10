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
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        TrackOut(
            id=r.id,
            title=r.title,
            artist=r.artist,
            album=r.album,
            genre=r.genre,
            year=r.year,
            duration=r.duration,
            cover_art=r.cover_art,
            cover_url=_cover_url(r.cover_art),
        )
        for r in rows
    ]


@router.get("/playlists", response_model=list[PlaylistOut])
async def playlists(session: AsyncSession = Depends(get_session)) -> list[PlaylistOut]:
    rows = (await session.execute(select(LibraryPlaylist))).scalars().all()
    return [PlaylistOut(id=r.id, name=r.name, song_count=r.song_count) for r in rows]


@router.get("/albums", response_model=list[AlbumOut])
async def albums(
    q: str = "", limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[AlbumOut]:
    stmt = select(LibraryAlbum)
    if q:
        stmt = stmt.where(LibraryAlbum.name.ilike(f"%{q}%"))
    rows = (await session.execute(stmt.limit(limit))).scalars().all()
    return [
        AlbumOut(
            id=r.id,
            name=r.name,
            artist=r.artist,
            year=r.year,
            cover_art=r.cover_art,
            cover_url=_cover_url(r.cover_art),
        )
        for r in rows
    ]


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
async def artists(session: AsyncSession = Depends(get_session)) -> list[ArtistOut]:
    rows = (await session.execute(select(LibraryArtist))).scalars().all()
    return [ArtistOut(id=r.id, name=r.name, album_count=r.album_count) for r in rows]


@router.get("/genres", response_model=list[str])
async def genres(session: AsyncSession = Depends(get_session)) -> list[str]:
    stmt = select(distinct(LibraryTrack.genre)).where(LibraryTrack.genre.is_not(None))
    return [g for g in (await session.execute(stmt)).scalars().all() if g]
