"""Synchronisation manuelle de la bibliothèque (§2, §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..providers.factory import ProviderNotConfigured, provider_from_session
from ..schemas import SyncResult
from ..services.library import LibrarySyncService

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("", response_model=SyncResult)
async def run_sync(session: AsyncSession = Depends(get_session)) -> SyncResult:
    try:
        provider = await provider_from_session(session)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        return await LibrarySyncService(session, provider).sync()
    finally:
        await provider.close()
