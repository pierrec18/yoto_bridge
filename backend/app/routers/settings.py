"""Configuration de la source musicale et test de connexion (§1, §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..providers.subsonic import SubsonicProvider
from ..schemas import ConnectionTestResult, SettingsIn, SettingsOut, StreamTokenOut
from ..security import get_or_create_settings, new_stream_token
from ..secrets import decrypt, encrypt, is_set
from ..services.playback import clear_resolution_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_out(settings) -> SettingsOut:
    return SettingsOut(
        provider=settings.provider,
        navidrome_url=settings.navidrome_url,
        username=settings.username,
        stream_token=decrypt(settings.stream_token),
        configured=bool(settings.navidrome_url and settings.username and is_set(settings.password)),
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
    settings.password = encrypt(payload.password)
    await session.commit()
    clear_resolution_cache()
    return _to_out(settings)


@router.post("/reset-token", response_model=StreamTokenOut)
async def reset_stream_token(session: AsyncSession = Depends(get_session)) -> StreamTokenOut:
    """Régénère le jeton de streaming. Les anciennes URLs Yoto deviennent invalides."""
    settings = await get_or_create_settings(session)
    settings.stream_token = encrypt(new_stream_token())
    await session.commit()
    return StreamTokenOut(stream_token=decrypt(settings.stream_token) or "")


@router.post("/test", response_model=ConnectionTestResult)
async def test_connection(payload: SettingsIn) -> ConnectionTestResult:
    provider = SubsonicProvider(payload.navidrome_url, payload.username, payload.password)
    try:
        await provider.ping()
        return ConnectionTestResult(ok=True, detail="Connexion réussie")
    except Exception:  # noqa: BLE001 - ne jamais renvoyer une réponse distante brute
        return ConnectionTestResult(ok=False, detail="Connexion impossible : vérifiez l'URL et les identifiants")
    finally:
        await provider.close()
