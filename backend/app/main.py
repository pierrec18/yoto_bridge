"""Point d'entrée FastAPI du Yoto Radio Server."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .database import init_db
from .routers import cards, library, settings, stats, stream, sync, yoto
from .scheduler import periodic_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


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
    allow_origins=[o.strip() for o in _config.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
