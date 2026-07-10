"""OAuth Authorization Code + PKCE pour l'API Yoto (§18).

Flux navigateur : l'utilisateur se connecte sur login.yotoplay.com, Yoto
redirige vers notre callback avec un `code`, qu'on échange (avec le
`code_verifier` PKCE) contre un access token + refresh token.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from ..config import get_config


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_pkce() -> tuple[str, str]:
    """Renvoie (code_verifier, code_challenge) — PKCE S256."""
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def generate_state() -> str:
    return secrets.token_urlsafe(16)


def redirect_uri() -> str:
    return f"{get_config().public_base_url.rstrip('/')}/api/yoto/callback"


def build_authorize_url(client_id: str, state: str, code_challenge: str) -> str:
    cfg = get_config()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "scope": cfg.yoto_scopes,
        "audience": cfg.yoto_audience,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{cfg.yoto_login_base}/authorize?{urlencode(params)}"


@dataclass(slots=True)
class TokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int


async def _post_token(data: dict[str, str], client: httpx.AsyncClient) -> TokenResponse:
    resp = await client.post(
        f"{get_config().yoto_login_base}/oauth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    payload = resp.json()
    return TokenResponse(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_in=int(payload.get("expires_in", 3600)),
    )


async def exchange_code(
    client_id: str, code: str, code_verifier: str, client: httpx.AsyncClient
) -> TokenResponse:
    return await _post_token(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri(),
        },
        client,
    )


async def refresh_token(
    client_id: str, refresh_token_value: str, client: httpx.AsyncClient
) -> TokenResponse:
    return await _post_token(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token_value,
        },
        client,
    )
