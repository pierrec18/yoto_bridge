"""Configuration de la source musicale et test de connexion (§1, §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Settings
from ..providers.subsonic import SubsonicProvider
from ..schemas import ConnectionTestResult, SettingsIn, SettingsOut
from ..services.playback import clear_resolution_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _load_or_create(session: AsyncSession) -> Settings:
    settings = await session.get(Settings, 1)
    if settings is None:
        settings = Settings(id=1)
        session.add(settings)
    return settings


@router.get("", response_model=SettingsOut)
async def read_settings(session: AsyncSession = Depends(get_session)) -> SettingsOut:
    settings = await _load_or_create(session)
    await session.commit()
    return SettingsOut(
        provider=settings.provider,
        navidrome_url=settings.navidrome_url,
        username=settings.username,
        configured=bool(settings.navidrome_url and settings.username and settings.password),
    )


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsIn, session: AsyncSession = Depends(get_session)
) -> SettingsOut:
    settings = await _load_or_create(session)
    settings.navidrome_url = payload.navidrome_url
    settings.username = payload.username
    settings.password = payload.password
    await session.commit()
    clear_resolution_cache()
    return SettingsOut(
        provider=settings.provider,
        navidrome_url=settings.navidrome_url,
        username=settings.username,
        configured=True,
    )


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
