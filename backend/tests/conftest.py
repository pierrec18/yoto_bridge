"""Fixtures de test : base SQLite isolée en mémoire."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    from app.services.playback import clear_resolution_cache

    clear_resolution_cache()
