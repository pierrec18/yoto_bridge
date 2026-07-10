"""Moteur SQLAlchemy asynchrone et gestion de session."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_config


class Base(DeclarativeBase):
    pass


_config = get_config()
engine = create_async_engine(_config.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _ensure_sqlite_dir(url: str) -> None:
    """Crée le dossier parent d'une base SQLite fichier si nécessaire."""
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return
    path = url[len(prefix) :]
    if path in ("", ":memory:") or path.startswith(":"):
        return
    parent = Path(path).expanduser().parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    """Crée les tables au démarrage (pas de migrations pour l'instant)."""
    from . import models  # noqa: F401  (enregistre les modèles)

    _ensure_sqlite_dir(_config.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI fournissant une session par requête."""
    async with SessionLocal() as session:
        yield session
