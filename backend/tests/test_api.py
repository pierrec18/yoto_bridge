"""Tests d'intégration de l'API cartes via ASGI (sans réseau)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_card_crud_flow(client: httpx.AsyncClient) -> None:
    # Création avec 3 pistes par défaut.
    resp = await client.post("/api/cards", json={"name": "Disney", "track_count": 3})
    assert resp.status_code == 201
    card = resp.json()
    assert card["track_count"] == 3
    assert len(card["tracks"]) == 3
    card_id = card["id"]

    # Configuration d'une piste en mode fixe.
    resp = await client.put(
        f"/api/cards/{card_id}/tracks/1",
        json={"track_number": 1, "mode": "fixed", "config": {"song_id": "s1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "fixed"

    # Duplication.
    resp = await client.post(f"/api/cards/{card_id}/duplicate")
    assert resp.status_code == 201
    assert resp.json()["name"] == "Disney (copie)"

    # Liste : 2 cartes.
    resp = await client.get("/api/cards")
    assert len(resp.json()) == 2

    # Suppression.
    resp = await client.delete(f"/api/cards/{card_id}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/cards/{card_id}")
    assert resp.status_code == 404


async def test_dashboard_without_config(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/stats/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["navidrome_configured"] is False
    assert data["navidrome_online"] is False


async def test_stream_unknown_track_returns_404(client: httpx.AsyncClient) -> None:
    resp = await client.get("/stream/999/1")
    assert resp.status_code == 404
