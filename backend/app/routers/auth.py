"""Authentification OpenID Connect optionnelle (Pocket ID et autres IdP)."""

from __future__ import annotations

from urllib.parse import urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..config import get_config

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth = OAuth()
_cfg = get_config()


def validate_auth_config() -> None:
    if not _cfg.auth_enabled:
        return
    missing = [
        name
        for name, value in (
            ("YOTO_OIDC_ISSUER_URL", _cfg.oidc_issuer_url),
            ("YOTO_OIDC_CLIENT_ID", _cfg.oidc_client_id),
            ("YOTO_OIDC_CLIENT_SECRET", _cfg.oidc_client_secret),
            ("YOTO_SESSION_SECRET", _cfg.session_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Configuration OIDC incomplète : {', '.join(missing)}")


if _cfg.auth_enabled:
    validate_auth_config()
    oauth.register(
        name="oidc",
        client_id=_cfg.oidc_client_id,
        client_secret=_cfg.oidc_client_secret,
        server_metadata_url=(
            f"{_cfg.oidc_issuer_url.rstrip('/')}/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": _cfg.oidc_scopes},
    )


class AuthStatus(BaseModel):
    enabled: bool
    authenticated: bool
    user: dict[str, str] | None = None


def _safe_next(value: str | None) -> str:
    """N'accepte qu'un chemin local pour éviter les redirections ouvertes."""
    if not value:
        return "/"
    parsed = urlparse(value)
    return value if not parsed.scheme and not parsed.netloc and value.startswith("/") else "/"


@router.get("/status", response_model=AuthStatus)
async def status(request: Request) -> AuthStatus:
    user = request.session.get("user") if _cfg.auth_enabled else None
    return AuthStatus(
        enabled=_cfg.auth_enabled,
        authenticated=not _cfg.auth_enabled or bool(user),
        user=user,
    )


@router.get("/login")
async def login(request: Request, next: str | None = None) -> RedirectResponse:
    if not _cfg.auth_enabled:
        return RedirectResponse(_safe_next(next), status_code=303)
    request.session["next"] = _safe_next(next)
    client = oauth.create_client("oidc")
    if client is None:  # pragma: no cover - validé au démarrage
        raise HTTPException(status_code=503, detail="Client OIDC indisponible")
    redirect_uri = f"{_cfg.public_base_url.rstrip('/')}/api/auth/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    if not _cfg.auth_enabled:
        return RedirectResponse("/", status_code=303)
    client = oauth.create_client("oidc")
    if client is None:  # pragma: no cover - validé au démarrage
        raise HTTPException(status_code=503, detail="Client OIDC indisponible")
    token = await client.authorize_access_token(request)
    claims = token.get("userinfo") or {}
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Identité OIDC invalide")
    request.session["user"] = {
        "sub": str(claims["sub"]),
        "name": str(claims.get("name") or claims.get("preferred_username") or ""),
        "email": str(claims.get("email") or ""),
    }
    destination = _safe_next(request.session.pop("next", "/"))
    return RedirectResponse(destination, status_code=303)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/", status_code=303)
