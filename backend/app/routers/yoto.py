"""Intégration API officielle Yoto : OAuth + publication de cartes (§18)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_config
from ..database import get_session
from ..models import Card
from ..providers.factory import ProviderNotConfigured, build_provider
from ..schemas import PublishResult, YotoConfigIn, YotoLoginOut, YotoStatus
from ..security import get_or_create_settings
from ..secrets import decrypt, encrypt, is_set
from ..yoto import oauth
from ..yoto.client import YotoClient, YotoError, YotoNotConnected

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/yoto", tags=["yoto"])


@router.get("/status", response_model=YotoStatus)
async def status(session: AsyncSession = Depends(get_session)) -> YotoStatus:
    settings = await get_or_create_settings(session)
    await session.commit()
    return YotoStatus(
        client_id_set=bool(settings.yoto_client_id),
        connected=is_set(settings.yoto_refresh_token),
        redirect_uri=oauth.redirect_uri(),
    )


@router.put("/config", response_model=YotoStatus)
async def set_config(
    payload: YotoConfigIn, session: AsyncSession = Depends(get_session)
) -> YotoStatus:
    settings = await get_or_create_settings(session)
    settings.yoto_client_id = payload.client_id.strip()
    await session.commit()
    return YotoStatus(
        client_id_set=True,
        connected=is_set(settings.yoto_refresh_token),
        redirect_uri=oauth.redirect_uri(),
    )


@router.get("/login", response_model=YotoLoginOut)
async def login(session: AsyncSession = Depends(get_session)) -> YotoLoginOut:
    settings = await get_or_create_settings(session)
    if not settings.yoto_client_id:
        raise HTTPException(status_code=409, detail="client_id Yoto non configuré")
    verifier, challenge = oauth.generate_pkce()
    state = oauth.generate_state()
    settings.yoto_pkce_verifier = encrypt(verifier)
    settings.yoto_pkce_state = encrypt(state)
    await session.commit()
    return YotoLoginOut(
        authorize_url=oauth.build_authorize_url(settings.yoto_client_id, state, challenge)
    )


@router.get("/callback")
async def callback(
    code: str, state: str, session: AsyncSession = Depends(get_session)
) -> RedirectResponse:
    settings = await get_or_create_settings(session)
    frontend = f"{get_config().public_base_url.rstrip('/')}/settings"
    stored_state = decrypt(settings.yoto_pkce_state)
    verifier = decrypt(settings.yoto_pkce_verifier)
    if not stored_state or state != stored_state:
        return RedirectResponse(f"{frontend}?yoto=error", status_code=303)
    if not settings.yoto_client_id or not verifier:
        return RedirectResponse(f"{frontend}?yoto=error", status_code=303)

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            tokens = await oauth.exchange_code(
                settings.yoto_client_id, code, verifier, client
            )
        except httpx.HTTPStatusError:
            logger.exception("Échec de l'échange OAuth Yoto")
            return RedirectResponse(f"{frontend}?yoto=error", status_code=303)

    from datetime import datetime, timedelta, timezone

    settings.yoto_access_token = encrypt(tokens.access_token)
    settings.yoto_refresh_token = encrypt(tokens.refresh_token)
    settings.yoto_token_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=tokens.expires_in
    )
    settings.yoto_pkce_verifier = None
    settings.yoto_pkce_state = None
    await session.commit()
    return RedirectResponse(f"{frontend}?yoto=connected", status_code=303)


@router.post("/disconnect", response_model=YotoStatus)
async def disconnect(session: AsyncSession = Depends(get_session)) -> YotoStatus:
    settings = await get_or_create_settings(session)
    settings.yoto_access_token = None
    settings.yoto_refresh_token = None
    settings.yoto_token_expires_at = None
    await session.commit()
    return YotoStatus(
        client_id_set=bool(settings.yoto_client_id),
        connected=False,
        redirect_uri=oauth.redirect_uri(),
    )


@router.post("/cards/{card_id}/publish", response_model=PublishResult)
async def publish(card_id: int, session: AsyncSession = Depends(get_session)) -> PublishResult:
    from ..services.publish import PublishError, PublishService

    card = (
        await session.execute(
            select(Card).where(Card.id == card_id).options(selectinload(Card.tracks))
        )
    ).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Carte introuvable")

    settings = await get_or_create_settings(session)
    try:
        provider = build_provider(settings)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    yoto = YotoClient(settings, session.commit)
    try:
        service = PublishService(session, settings, yoto, provider)
        result = await service.publish(card)
        await session.commit()
        return PublishResult(**result)
    except YotoNotConnected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (PublishError, YotoError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await yoto.close()
        await provider.close()
