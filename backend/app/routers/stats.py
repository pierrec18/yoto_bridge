"""Dashboard et statistiques (§8, §13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Card, HistoryEntry, LibraryTrack, Settings
from ..providers.factory import ProviderNotConfigured, build_provider
from ..schemas import DashboardStats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(session: AsyncSession = Depends(get_session)) -> DashboardStats:
    settings = await session.get(Settings, 1)
    configured = bool(
        settings and settings.navidrome_url and settings.username and settings.password
    )
    online = False
    if configured and settings is not None:
        try:
            provider = build_provider(settings)
            try:
                online = await provider.ping()
            finally:
                await provider.close()
        except (ProviderNotConfigured, Exception):  # noqa: BLE001
            online = False

    cards = await session.scalar(select(func.count()).select_from(Card)) or 0
    tracks = await session.scalar(select(func.count()).select_from(LibraryTrack)) or 0
    plays = await session.scalar(select(func.count()).select_from(HistoryEntry)) or 0
    return DashboardStats(
        navidrome_configured=configured,
        navidrome_online=online,
        cards=cards,
        tracks=tracks,
        plays=plays,
    )


@router.get("/top-tracks")
async def top_tracks(limit: int = 10, session: AsyncSession = Depends(get_session)) -> list[dict]:
    stmt = (
        select(
            HistoryEntry.song_id,
            HistoryEntry.song_title,
            HistoryEntry.artist,
            func.count().label("plays"),
        )
        .group_by(HistoryEntry.song_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"song_id": r.song_id, "title": r.song_title, "artist": r.artist, "plays": r.plays}
        for r in rows
    ]
