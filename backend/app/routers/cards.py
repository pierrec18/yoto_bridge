"""Gestion des cartes et de leur mapping de pistes (§3, §4, §9, §10)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session
from ..models import Card, CardTrack, HistoryEntry, PlaybackMode
from ..providers.factory import ProviderNotConfigured, provider_from_session
from ..schemas import CardIn, CardOut, CardTrackIn, CardTrackOut, HistoryOut

router = APIRouter(prefix="/api/cards", tags=["cards"])


async def _get_card(session: AsyncSession, card_id: int) -> Card:
    card = (
        await session.execute(
            select(Card).where(Card.id == card_id).options(selectinload(Card.tracks))
        )
    ).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    return card


def _default_tracks(count: int) -> list[CardTrack]:
    return [
        CardTrack(track_number=n, mode=PlaybackMode.RANDOM, config={})
        for n in range(1, count + 1)
    ]


@router.get("", response_model=list[CardOut])
async def list_cards(session: AsyncSession = Depends(get_session)) -> list[Card]:
    cards = (
        await session.execute(select(Card).options(selectinload(Card.tracks)))
    ).scalars().all()
    return list(cards)


@router.post("", response_model=CardOut, status_code=201)
async def create_card(payload: CardIn, session: AsyncSession = Depends(get_session)) -> Card:
    card = Card(
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        track_count=payload.track_count,
        tracks=_default_tracks(payload.track_count),
    )
    session.add(card)
    await session.commit()
    return await _get_card(session, card.id)


@router.get("/{card_id}", response_model=CardOut)
async def get_card(card_id: int, session: AsyncSession = Depends(get_session)) -> Card:
    return await _get_card(session, card_id)


@router.put("/{card_id}", response_model=CardOut)
async def update_card(
    card_id: int, payload: CardIn, session: AsyncSession = Depends(get_session)
) -> Card:
    card = await _get_card(session, card_id)
    card.name = payload.name
    card.description = payload.description
    card.image_url = payload.image_url
    _resize_tracks(card, payload.track_count)
    await session.commit()
    return await _get_card(session, card_id)


def _resize_tracks(card: Card, new_count: int) -> None:
    current = {t.track_number: t for t in card.tracks}
    if new_count > card.track_count:
        for n in range(card.track_count + 1, new_count + 1):
            if n not in current:
                card.tracks.append(CardTrack(track_number=n, mode=PlaybackMode.RANDOM, config={}))
    elif new_count < card.track_count:
        card.tracks = [t for t in card.tracks if t.track_number <= new_count]
    card.track_count = new_count


@router.delete("/{card_id}", status_code=204)
async def delete_card(card_id: int, session: AsyncSession = Depends(get_session)) -> None:
    card = await _get_card(session, card_id)
    await session.delete(card)
    await session.commit()


@router.post("/{card_id}/duplicate", response_model=CardOut, status_code=201)
async def duplicate_card(card_id: int, session: AsyncSession = Depends(get_session)) -> Card:
    source = await _get_card(session, card_id)
    clone = Card(
        name=f"{source.name} (copie)",
        description=source.description,
        image_url=source.image_url,
        track_count=source.track_count,
        tracks=[
            CardTrack(
                track_number=t.track_number,
                mode=t.mode,
                delivery=t.delivery,
                label=t.label,
                config=dict(t.config),
            )
            for t in source.tracks
        ],
    )
    session.add(clone)
    await session.commit()
    return await _get_card(session, clone.id)


# -- Mapping des pistes ---------------------------------------------------


@router.put("/{card_id}/tracks/{track_number}", response_model=CardTrackOut)
async def set_track(
    card_id: int,
    track_number: int,
    payload: CardTrackIn,
    session: AsyncSession = Depends(get_session),
) -> CardTrack:
    card = await _get_card(session, card_id)
    track = next((t for t in card.tracks if t.track_number == track_number), None)
    if track is None:
        track = CardTrack(track_number=track_number)
        card.tracks.append(track)
    track.mode = payload.mode
    track.delivery = payload.delivery
    track.label = payload.label
    track.config = payload.config
    track.position = 0
    track.last_song_id = None
    await session.commit()
    await session.refresh(track)
    return track


class GenerateRequest(BaseModel):
    """Génération automatique du mapping (§9)."""

    strategy: str = Field(
        default="playlist_expand",
        description="playlist_expand | album_expand | all_random | playlist | album",
    )
    source_id: str | None = None


@router.post("/{card_id}/generate", response_model=CardOut)
async def generate_tracks(
    card_id: int,
    payload: GenerateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> Card:
    card = await _get_card(session, card_id)
    count = card.track_count or len(card.tracks)
    if count == 0:
        raise HTTPException(status_code=400, detail="La carte n'a aucune piste")

    new_tracks: list[CardTrack]
    if payload.strategy in {"playlist_expand", "album_expand"}:
        if not payload.source_id:
            raise HTTPException(status_code=400, detail="source_id requis")
        try:
            provider = await provider_from_session(session)
        except ProviderNotConfigured as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        try:
            if payload.strategy == "playlist_expand":
                songs = await provider.get_playlist_tracks(payload.source_id)
            else:
                songs = await provider.get_album_tracks(payload.source_id)
        finally:
            await provider.close()
        new_tracks = [
            CardTrack(
                track_number=i + 1,
                mode=PlaybackMode.FIXED,
                label=song.title,
                config={"song_id": song.id},
            )
            for i, song in enumerate(songs[:count])
        ]
    elif payload.strategy == "all_random":
        new_tracks = [
            CardTrack(track_number=n, mode=PlaybackMode.RANDOM, config={})
            for n in range(1, count + 1)
        ]
    elif payload.strategy in {"playlist", "album"}:
        if not payload.source_id:
            raise HTTPException(status_code=400, detail="source_id requis")
        key = "playlist_id" if payload.strategy == "playlist" else "album_id"
        mode = PlaybackMode.PLAYLIST if payload.strategy == "playlist" else PlaybackMode.ALBUM
        new_tracks = [
            CardTrack(track_number=n, mode=mode, config={key: payload.source_id})
            for n in range(1, count + 1)
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {payload.strategy}")

    card.tracks = new_tracks
    card.track_count = len(new_tracks)
    await session.commit()
    return await _get_card(session, card_id)


@router.get("/{card_id}/history", response_model=list[HistoryOut])
async def card_history(
    card_id: int, limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[HistoryEntry]:
    rows = (
        await session.execute(
            select(HistoryEntry)
            .where(HistoryEntry.card_id == card_id)
            .order_by(HistoryEntry.played_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)
