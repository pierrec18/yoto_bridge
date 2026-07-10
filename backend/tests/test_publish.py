"""Tests du service de publication Yoto (stream + hors ligne)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardTrack, Delivery, PlaybackMode, Settings, YotoMedia
from app.providers.base import ProviderTrack
from app.services.publish import PublishError, PublishService
from tests.fakes import FakeProvider

pytestmark = pytest.mark.asyncio


class FakeYoto:
    def __init__(self) -> None:
        self.uploads = 0
        self.content_body: dict[str, Any] | None = None

    async def get_upload_url(self) -> tuple[str, str]:
        return "https://upload.example/put", "up-1"

    async def upload_bytes(self, url: str, data: bytes, content_type: str) -> None:
        self.uploads += 1

    async def poll_transcoded(self, upload_id: str) -> dict[str, Any]:
        return {
            "transcodedSha256": "deadbeef",
            "transcodedInfo": {
                "duration": 180,
                "fileSize": 4200,
                "channels": 2,
                "format": "mp3",
                "metadata": {"title": "Hakuna Matata"},
            },
        }

    async def create_or_update_content(self, body: dict[str, Any]) -> dict[str, Any]:
        self.content_body = body
        return {"cardId": "card-abc"}

    async def upload_icon(self, data: bytes, content_type: str, *, filename: str) -> str:
        return "icon-media"


async def _settings(session: AsyncSession) -> Settings:
    s = Settings(id=1, stream_token="tok", yoto_client_id="c", yoto_refresh_token="r")
    session.add(s)
    await session.commit()
    return s


async def test_publish_mixes_stream_and_offline(session: AsyncSession) -> None:
    settings = await _settings(session)
    card = Card(name="Disney", track_count=2)
    card.tracks.append(CardTrack(track_number=1, mode=PlaybackMode.RANDOM, delivery=Delivery.STREAM))
    card.tracks.append(
        CardTrack(
            track_number=2,
            mode=PlaybackMode.FIXED,
            delivery=Delivery.OFFLINE,
            config={"song_id": "s1"},
        )
    )
    session.add(card)
    await session.commit()

    provider = FakeProvider(
        tracks={
            "s1": ProviderTrack(id="s1", title="Hakuna Matata", cover_art="cover-1")
        }
    )
    yoto = FakeYoto()
    result = await PublishService(session, settings, yoto, provider).publish(card)  # type: ignore[arg-type]

    assert result["chapters"] == 2
    assert result["yoto_card_id"] == "card-abc"
    assert card.yoto_card_id == "card-abc"
    assert yoto.uploads == 1

    chapters = yoto.content_body["content"]["chapters"]
    stream_track = chapters[0]["tracks"][0]
    offline_track = chapters[1]["tracks"][0]
    assert stream_track["type"] == "stream"
    assert stream_track["trackUrl"].endswith("/stream/{}/1?t=tok".format(card.id))
    assert offline_track["type"] == "audio"
    assert offline_track["trackUrl"] == "yoto:#deadbeef"
    assert chapters[1]["display"] == {"icon16x16": "yoto:#icon-media"}
    assert offline_track["display"] == {"icon16x16": "yoto:#icon-media"}

    # Média mis en cache pour éviter un ré-upload.
    cached = await session.get(YotoMedia, "s1")
    assert cached is not None and cached.sha256 == "deadbeef"


async def test_publish_reuses_cached_media(session: AsyncSession) -> None:
    settings = await _settings(session)
    session.add(YotoMedia(song_id="s1", sha256="cafe", duration=10, file_size=99, format="mp3"))
    card = Card(name="C", track_count=1)
    card.tracks.append(
        CardTrack(
            track_number=1,
            mode=PlaybackMode.FIXED,
            delivery=Delivery.OFFLINE,
            config={"song_id": "s1"},
        )
    )
    session.add(card)
    await session.commit()

    yoto = FakeYoto()
    await PublishService(session, settings, yoto, FakeProvider()).publish(card)  # type: ignore[arg-type]
    assert yoto.uploads == 0  # déjà en cache
    assert yoto.content_body["content"]["chapters"][0]["tracks"][0]["trackUrl"] == "yoto:#cafe"


async def test_publish_rejects_offline_non_fixed(session: AsyncSession) -> None:
    settings = await _settings(session)
    card = Card(name="C", track_count=1)
    card.tracks.append(
        CardTrack(track_number=1, mode=PlaybackMode.RANDOM, delivery=Delivery.OFFLINE)
    )
    session.add(card)
    await session.commit()

    with pytest.raises(PublishError):
        await PublishService(session, settings, FakeYoto(), FakeProvider()).publish(card)  # type: ignore[arg-type]
