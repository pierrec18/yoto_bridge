"""Schémas Pydantic exposés par l'API REST (§10)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import Delivery, PlaybackMode


class SettingsIn(BaseModel):
    navidrome_url: str
    username: str
    password: str


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    navidrome_url: str | None = None
    username: str | None = None
    stream_token: str | None = None
    configured: bool = False


class StreamTokenOut(BaseModel):
    stream_token: str


class ConnectionTestResult(BaseModel):
    ok: bool
    detail: str


class CardTrackIn(BaseModel):
    track_number: int = Field(ge=1)
    mode: PlaybackMode = PlaybackMode.RANDOM
    delivery: Delivery = Delivery.STREAM
    label: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class CardTrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_number: int
    mode: PlaybackMode
    delivery: Delivery
    label: str | None
    config: dict[str, Any]
    position: int
    last_song_id: str | None


class CardIn(BaseModel):
    name: str
    description: str | None = None
    image_url: str | None = None
    track_count: int = Field(default=1, ge=1, le=100)


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    image_url: str | None
    track_count: int
    yoto_card_id: str | None
    created_at: datetime
    updated_at: datetime
    tracks: list[CardTrackOut] = Field(default_factory=list)


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    track_number: int
    song_id: str
    song_title: str | None
    artist: str | None
    album: str | None
    played_at: datetime


class TrackOut(BaseModel):
    id: str
    title: str
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    year: int | None = None
    duration: int | None = None
    cover_art: str | None = None
    cover_url: str | None = None
    track_number: int | None = None
    disc_number: int | None = None


class PlaylistOut(BaseModel):
    id: str
    name: str
    song_count: int | None = None


class AlbumOut(BaseModel):
    id: str
    name: str
    artist: str | None = None
    year: int | None = None
    cover_art: str | None = None
    cover_url: str | None = None


class ArtistOut(BaseModel):
    id: str
    name: str
    album_count: int | None = None


class SyncResult(BaseModel):
    tracks: int
    albums: int
    playlists: int
    artists: int
    genres: int


class DashboardStats(BaseModel):
    navidrome_configured: bool
    navidrome_online: bool
    cards: int
    tracks: int
    plays: int


# -- Intégration Yoto (§18) ----------------------------------------------


class YotoStatus(BaseModel):
    client_id_set: bool
    connected: bool
    redirect_uri: str


class YotoConfigIn(BaseModel):
    client_id: str


class YotoLoginOut(BaseModel):
    authorize_url: str


class PublishResult(BaseModel):
    yoto_card_id: str | None
    chapters: int
