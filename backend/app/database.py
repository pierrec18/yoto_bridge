"""Moteur SQLAlchemy asynchrone et gestion de session."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
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
    """Crée les tables et applique les petites migrations SQLite intégrées."""
    from . import models  # noqa: F401  (enregistre les modèles)

    _ensure_sqlite_dir(_config.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "sqlite":
            await conn.run_sync(_migrate_sqlite)


def _migrate_sqlite(conn: Connection) -> None:
    """Ajoute les colonnes compatibles aux bases créées par les versions précédentes."""
    migrations = {
        "library_tracks": {
            "cover_art": "VARCHAR(128)",
            "track_number": "INTEGER",
            "disc_number": "INTEGER",
        },
        "library_albums": {"cover_art": "VARCHAR(128)"},
    }
    inspector = inspect(conn)
    for table, additions in migrations.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column, sql_type in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI fournissant une session par requête."""
    async with SessionLocal() as session:
        yield session
