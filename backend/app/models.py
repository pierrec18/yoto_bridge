"""Modèles ORM (§11)."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PlaybackMode(str, enum.Enum):
    """Stratégies de lecture d'une piste (§5)."""

    FIXED = "fixed"
    PLAYLIST = "playlist"
    ALBUM = "album"
    RANDOM = "random"
    SMART = "smart"
    SEARCH = "search"


class Delivery(str, enum.Enum):
    """Mode de livraison d'une piste vers la Yoto (§18)."""

    STREAM = "stream"  # type:stream, joué en streaming depuis ce serveur
    OFFLINE = "offline"  # fichier uploadé chez Yoto, écoutable hors ligne


class Settings(Base):
    """Configuration Navidrome (une seule ligne, id=1)."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(32), default="navidrome")
    navidrome_url: Mapped[str | None] = mapped_column(String(512))
    username: Mapped[str | None] = mapped_column(String(128))
    password: Mapped[str | None] = mapped_column(String(256))
    # Jeton partagé exigé sur les URLs /stream (déposé côté Yoto, révocable).
    stream_token: Mapped[str | None] = mapped_column(String(64))
    # Intégration API officielle Yoto (§18) — OAuth Authorization Code + PKCE.
    yoto_client_id: Mapped[str | None] = mapped_column(String(128))
    yoto_access_token: Mapped[str | None] = mapped_column(Text)
    yoto_refresh_token: Mapped[str | None] = mapped_column(Text)
    yoto_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    yoto_pkce_verifier: Mapped[str | None] = mapped_column(String(128))
    yoto_pkce_state: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Card(Base):
    """Une carte Yoto MYO (§3)."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    yoto_card_id: Mapped[str | None] = mapped_column(String(128))  # bonus §18
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    tracks: Mapped[list["CardTrack"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        order_by="CardTrack.track_number",
    )


class CardTrack(Base):
    """Mapping d'un numéro de piste vers une stratégie de lecture (§4)."""

    __tablename__ = "card_tracks"
    __table_args__ = (UniqueConstraint("card_id", "track_number", name="uq_card_track"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    track_number: Mapped[int] = mapped_column(Integer)
    mode: Mapped[PlaybackMode] = mapped_column(String(16), default=PlaybackMode.RANDOM)
    delivery: Mapped[Delivery] = mapped_column(String(16), default=Delivery.STREAM)
    label: Mapped[str | None] = mapped_column(String(255))
    # Configuration dépendant du mode : {"song_id": ...}, {"playlist_id": ...},
    # {"album_id": ...}, {"query": ..., "genre": ...}, etc.
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # État de progression pour les modes séquentiels (playlist / album).
    position: Mapped[int] = mapped_column(Integer, default=0)
    last_song_id: Mapped[str | None] = mapped_column(String(128))

    card: Mapped["Card"] = relationship(back_populates="tracks")


class HistoryEntry(Base):
    """Historique de lecture (§6, §12)."""

    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    track_number: Mapped[int] = mapped_column(Integer)
    song_id: Mapped[str] = mapped_column(String(128))
    song_title: Mapped[str | None] = mapped_column(String(512))
    artist: Mapped[str | None] = mapped_column(String(512))
    album: Mapped[str | None] = mapped_column(String(512))
    duration: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    played_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


# -- Cache bibliothèque (§2, §11) ----------------------------------------


class LibraryTrack(Base):
    __tablename__ = "library_tracks"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    artist: Mapped[str | None] = mapped_column(String(512))
    album: Mapped[str | None] = mapped_column(String(512))
    album_id: Mapped[str | None] = mapped_column(String(128))
    genre: Mapped[str | None] = mapped_column(String(128), index=True)
    year: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[int | None] = mapped_column(Integer)


class LibraryAlbum(Base):
    __tablename__ = "library_albums"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    artist: Mapped[str | None] = mapped_column(String(512))
    artist_id: Mapped[str | None] = mapped_column(String(128))
    year: Mapped[int | None] = mapped_column(Integer)
    genre: Mapped[str | None] = mapped_column(String(128))
    song_count: Mapped[int | None] = mapped_column(Integer)


class LibraryPlaylist(Base):
    __tablename__ = "library_playlists"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    song_count: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[int | None] = mapped_column(Integer)


class LibraryArtist(Base):
    __tablename__ = "library_artists"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    album_count: Mapped[int | None] = mapped_column(Integer)


class YotoMedia(Base):
    """Cache des uploads Yoto : évite de re-transcoder un même morceau (§18)."""

    __tablename__ = "yoto_media"

    song_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(512))
    duration: Mapped[int | None] = mapped_column(Integer)
    file_size: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
