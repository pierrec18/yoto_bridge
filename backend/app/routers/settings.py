"""Configuration de la source musicale et test de connexion (§1, §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..providers.subsonic import SubsonicProvider
from ..schemas import ConnectionTestResult, SettingsIn, SettingsOut, StreamTokenOut
from ..security import get_or_create_settings, new_stream_token
from ..services.playback import clear_resolution_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_out(settings) -> SettingsOut:
    return SettingsOut(
        provider=settings.provider,
        navidrome_url=settings.navidrome_url,
        username=settings.username,
        stream_token=settings.stream_token,
        configured=bool(settings.navidrome_url and settings.username and settings.password),
    )


@router.get("", response_model=SettingsOut)
async def read_settings(session: AsyncSession = Depends(get_session)) -> SettingsOut:
    settings = await get_or_create_settings(session)
    await session.commit()
    return _to_out(settings)


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsIn, session: AsyncSession = Depends(get_session)
) -> SettingsOut:
    settings = await get_or_create_settings(session)
    settings.navidrome_url = payload.navidrome_url
    settings.username = payload.username
    settings.password = payload.password
    await session.commit()
    clear_resolution_cache()
    return _to_out(settings)


@router.post("/reset-token", response_model=StreamTokenOut)
async def reset_stream_token(session: AsyncSession = Depends(get_session)) -> StreamTokenOut:
    """Régénère le jeton de streaming. Les anciennes URLs Yoto deviennent invalides."""
    settings = await get_or_create_settings(session)
    settings.stream_token = new_stream_token()
    await session.commit()
    return StreamTokenOut(stream_token=settings.stream_token)


@router.post("/test", response_model=ConnectionTestResult)
async def test_connection(payload: SettingsIn) -> ConnectionTestResult:
    provider = SubsonicProvider(payload.navidrome_url, payload.username, payload.password)
    try:
        await provider.ping()
        return ConnectionTestResult(ok=True, detail="Connexion réussie")
    except Exception as exc:  # noqa: BLE001 - on renvoie le message à l'UI
        return ConnectionTestResult(ok=False, detail=str(exc))
    finally:
        await provider.close()
