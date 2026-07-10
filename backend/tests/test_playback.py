"""Tests du résolveur de lecture (§5, §6)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardTrack, LibraryTrack, PlaybackMode
from app.providers.base import ProviderTrack
from app.services.playback import PlaybackService, ResolutionError
from tests.fakes import FakeProvider

pytestmark = pytest.mark.asyncio


async def _make_card_track(session: AsyncSession, **kwargs) -> CardTrack:
    card = Card(name="Test", track_count=1)
    track = CardTrack(track_number=1, **kwargs)
    card.tracks.append(track)
    session.add(card)
    await session.commit()
    return track


async def test_fixed_returns_configured_song(session: AsyncSession) -> None:
    song = ProviderTrack(id="s1", title="Hakuna Matata")
    provider = FakeProvider(tracks={"s1": song})
    ct = await _make_card_track(session, mode=PlaybackMode.FIXED, config={"song_id": "s1"})

    result = await PlaybackService(session, provider).resolve(ct)

    assert result.id == "s1"
    assert result.title == "Hakuna Matata"


async def test_fixed_without_song_id_raises(session: AsyncSession) -> None:
    ct = await _make_card_track(session, mode=PlaybackMode.FIXED, config={})
    with pytest.raises(ResolutionError):
        await PlaybackService(session, FakeProvider()).resolve(ct)


async def test_playlist_advances_and_cycles(session: AsyncSession) -> None:
    songs = [ProviderTrack(id=f"s{i}", title=f"T{i}") for i in range(3)]
    provider = FakeProvider(playlists={"p1": songs})
    ct = await _make_card_track(
        session, mode=PlaybackMode.PLAYLIST, config={"playlist_id": "p1"}
    )
    service = PlaybackService(session, provider)

    seen = []
    for _ in range(4):
        result = await service.resolve(ct)
        seen.append(result.id)
        # Neutralise le cache TTL pour forcer l'avancement.
        from app.services.playback import clear_resolution_cache

        clear_resolution_cache()

    assert seen == ["s0", "s1", "s2", "s0"]


async def test_random_excludes_last_song(session: AsyncSession) -> None:
    session.add_all(
        [
            LibraryTrack(id="a", title="A", artist="X", album="Alb"),
            LibraryTrack(id="b", title="B", artist="Y", album="Alb2"),
        ]
    )
    ct = await _make_card_track(session, mode=PlaybackMode.RANDOM, config={})
    ct.last_song_id = "a"
    await session.commit()

    result = await PlaybackService(session, FakeProvider()).resolve(ct)
    assert result.id == "b"


async def test_resolution_cache_returns_same_song(session: AsyncSession) -> None:
    songs = [ProviderTrack(id=f"s{i}", title=f"T{i}") for i in range(3)]
    provider = FakeProvider(playlists={"p1": songs})
    ct = await _make_card_track(
        session, mode=PlaybackMode.PLAYLIST, config={"playlist_id": "p1"}
    )
    service = PlaybackService(session, provider)

    first = await service.resolve(ct)
    second = await service.resolve(ct)  # doit venir du cache, sans avancer
    assert first.id == second.id == "s0"
