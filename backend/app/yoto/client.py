"""Client de l'API Yoto : gestion du token, upload/transcode, contenu (§18)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import get_config
from ..models import Settings
from . import oauth


class YotoNotConnected(RuntimeError):
    """Aucun compte Yoto connecté (pas de refresh token)."""


class YotoError(RuntimeError):
    """Erreur renvoyée par l'API Yoto."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalise les dates SQLite, qui sont relues sans information de fuseau."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class YotoClient:
    """Encapsule les appels Yoto pour une ligne de réglages donnée.

    Rafraîchit le token à la volée et persiste les nouveaux jetons.
    """

    def __init__(
        self,
        settings: Settings,
        commit,  # coroutine sans argument qui persiste les settings
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._commit = commit
        self._client = client or httpx.AsyncClient(timeout=60.0)
        self._cfg = get_config()

    async def _access_token(self) -> str:
        s = self._settings
        if not s.yoto_refresh_token or not s.yoto_client_id:
            raise YotoNotConnected("Compte Yoto non connecté")
        valid = (
            s.yoto_access_token
            and s.yoto_token_expires_at
            and _as_utc(s.yoto_token_expires_at) > _now() + timedelta(seconds=60)
        )
        if valid:
            return s.yoto_access_token  # type: ignore[return-value]
        # Rafraîchissement.
        tokens = await oauth.refresh_token(s.yoto_client_id, s.yoto_refresh_token, self._client)
        s.yoto_access_token = tokens.access_token
        if tokens.refresh_token:  # rotation : le refresh token change à chaque usage
            s.yoto_refresh_token = tokens.refresh_token
        s.yoto_token_expires_at = _now() + timedelta(seconds=tokens.expires_in)
        await self._commit()
        return tokens.access_token

    async def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self._access_token()}", "Accept": "application/json"}

    # -- Upload / transcodage --------------------------------------------

    async def get_upload_url(self) -> tuple[str, str]:
        resp = await self._client.get(
            f"{self._cfg.yoto_api_base}/media/transcode/audio/uploadUrl",
            headers=await self._headers(),
        )
        resp.raise_for_status()
        upload = resp.json().get("upload", {})
        return upload["uploadUrl"], upload["uploadId"]

    async def upload_bytes(self, upload_url: str, data: bytes, content_type: str) -> None:
        resp = await self._client.put(
            upload_url, content=data, headers={"Content-Type": content_type}
        )
        resp.raise_for_status()

    async def poll_transcoded(
        self, upload_id: str, *, attempts: int = 60, interval: float = 1.0
    ) -> dict[str, Any]:
        headers = await self._headers()
        url = f"{self._cfg.yoto_api_base}/media/upload/{upload_id}/transcoded?loudnorm=false"
        for _ in range(attempts):
            resp = await self._client.get(url, headers=headers)
            resp.raise_for_status()
            transcode = resp.json().get("transcode", {})
            if transcode.get("transcodedSha256"):
                return transcode
            await asyncio.sleep(interval)
        raise YotoError("Transcodage Yoto trop long (timeout)")

    # -- Contenu ----------------------------------------------------------

    async def create_or_update_content(self, body: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self._cfg.yoto_api_base}/content",
            json=body,
            headers={**await self._headers(), "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise YotoError(f"Yoto /content {resp.status_code} : {resp.text}")
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
