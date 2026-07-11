"""Point d'entrée FastAPI du Yoto Radio Server."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .auth import OIDCAuthMiddleware
from .config import get_config
from .csrf import CSRFMiddleware
from .database import init_db
from .routers import auth, cards, library, settings, stats, stream, sync, yoto
from .scheduler import periodic_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# Les URLs Subsonic et /stream contiennent des jetons à usage limité. Ne pas
# les recopier dans les logs d'accès ou dans les logs de transport HTTP.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    sync_task = asyncio.create_task(periodic_sync())
    try:
        yield
    finally:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Yoto Radio Server",
    version="0.1.0",
    description="Pont entre une bibliothèque Navidrome et des cartes Yoto MYO.",
    lifespan=lifespan,
)

_config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.cors_origin_list(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
    allow_credentials=True,
)
# SessionMiddleware doit envelopper le middleware d'authentification pour que
# request.session soit disponible pendant le contrôle d'accès.
app.add_middleware(OIDCAuthMiddleware)
# Ce middleware doit être ajouté avant SessionMiddleware : il s'exécute alors
# après la création de request.session, mais avant le routage FastAPI.
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=_config.session_secret or "auth-disabled",
    max_age=_config.session_max_age_seconds,
    same_site="lax",
    https_only=_config.public_base_url.startswith("https://"),
)

app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(sync.router)
app.include_router(library.router)
app.include_router(cards.router)
app.include_router(stats.router)
app.include_router(yoto.router)
app.include_router(stream.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
