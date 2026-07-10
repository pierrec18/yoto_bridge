"""Tests du provider Subsonic : authentification par token et mapping."""

from __future__ import annotations

import hashlib

import httpx
import pytest

from app.providers.subsonic import SubsonicProvider

pytestmark = pytest.mark.asyncio

_PASSWORD = "s3cret"


def _ok(body: dict) -> dict:
    return {"subsonic-response": {"status": "ok", **body}}


def _handler_factory(captured: list[httpx.Request], body: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_ok(body))

    return handler


async def test_auth_uses_salted_token() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_handler_factory(captured, {}))
    client = httpx.AsyncClient(transport=transport)
    provider = SubsonicProvider("http://nav", "user", _PASSWORD, client=client)

    assert await provider.ping() is True

    req = captured[0]
    salt = req.url.params["s"]
    token = req.url.params["t"]
    expected = hashlib.md5(f"{_PASSWORD}{salt}".encode()).hexdigest()
    assert token == expected
    assert req.url.params["u"] == "user"
    assert _PASSWORD not in str(req.url)  # le mot de passe n'est jamais transmis en clair
    await provider.close()


async def test_get_playlists_mapping() -> None:
    body = {"playlists": {"playlist": [{"id": "10", "name": "Disney", "songCount": 42}]}}
    transport = httpx.MockTransport(_handler_factory([], body))
    client = httpx.AsyncClient(transport=transport)
    provider = SubsonicProvider("http://nav", "user", _PASSWORD, client=client)

    playlists = await provider.get_playlists()
    assert len(playlists) == 1
    assert playlists[0].id == "10"
    assert playlists[0].name == "Disney"
    assert playlists[0].song_count == 42
    await provider.close()


async def test_stream_forwards_range_and_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Range") == "bytes=100-"
        return httpx.Response(206, content=b"audiodata", headers={"content-type": "audio/mpeg"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = SubsonicProvider("http://nav", "user", _PASSWORD, client=client)

    result = await provider.stream("42", range_header="bytes=100-")
    assert result.status_code == 206
    assert result.content_type == "audio/mpeg"
    chunks = [c async for c in result.body]
    assert b"".join(chunks) == b"audiodata"
    await provider.close()


async def test_cover_art_is_proxied() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/rest/getCoverArt.view")
        assert request.url.params["id"] == "cover-42"
        assert request.url.params["size"] == "300"
        return httpx.Response(200, content=b"jpeg", headers={"content-type": "image/jpeg"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SubsonicProvider("http://nav", "user", _PASSWORD, client=client)
    result = await provider.get_cover_art("cover-42")
    assert result.content_type == "image/jpeg"
    assert b"".join([chunk async for chunk in result.body]) == b"jpeg"
    await provider.close()


async def test_error_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"subsonic-response": {"status": "failed", "error": {"message": "bad login"}}},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = SubsonicProvider("http://nav", "user", "wrong", client=client)

    from app.providers.subsonic import SubsonicError

    with pytest.raises(SubsonicError, match="bad login"):
        await provider.ping()
    await provider.close()
