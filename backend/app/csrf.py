"""Protection CSRF pour les appels API authentifiés par cookie OIDC.

SameSite=Lax réduit déjà fortement le risque, mais le double-submit cookie
protège aussi les requêtes cross-site qui pourraient être émises par un
navigateur compromis ou une intégration future.
"""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import get_config

_COOKIE = "yoto_csrf"
_HEADER = "x-csrf-token"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cfg = get_config()
        protected = (
            cfg.auth_enabled
            and request.method not in _SAFE_METHODS
            and request.url.path.startswith("/api/")
            and request.url.path != "/api/auth/logout"
        )
        if protected and request.session.get("user"):
            cookie = request.cookies.get(_COOKIE)
            header = request.headers.get(_HEADER)
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "Jeton CSRF invalide"}, status_code=403)

        response = await call_next(request)
        if cfg.auth_enabled and not request.cookies.get(_COOKIE):
            response.set_cookie(
                _COOKIE,
                secrets.token_urlsafe(32),
                max_age=cfg.session_max_age_seconds,
                secure=cfg.public_base_url.startswith("https://"),
                httponly=False,
                samesite="lax",
                path="/",
            )
        return response
