"""Middleware de protection de l'interface API par session OIDC."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from .config import get_config


class OIDCAuthMiddleware(BaseHTTPMiddleware):
    """Protège l'API, tout en laissant les flux Yoto tokenisés accessibles."""

    _PUBLIC_PREFIXES = ("/api/auth/", "/stream/")
    _PUBLIC_PATHS = {"/health", "/api/yoto/callback"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cfg = get_config()
        path = request.url.path
        if (
            not cfg.auth_enabled
            or path in self._PUBLIC_PATHS
            or any(path.startswith(prefix) for prefix in self._PUBLIC_PREFIXES)
            or request.session.get("user")
        ):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentification requise"}, status_code=401)
        return RedirectResponse(f"/api/auth/login?next={path}", status_code=303)
