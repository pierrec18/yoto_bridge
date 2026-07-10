"""Tests du flux OAuth PKCE Yoto."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.models import Settings
from app.yoto import oauth
from app.yoto.client import YotoClient


def test_pkce_challenge_matches_verifier() -> None:
    verifier, challenge = oauth.generate_pkce()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == expected
    assert 43 <= len(verifier) <= 128


def test_authorize_url_contains_required_params() -> None:
    url = oauth.build_authorize_url("client-123", "state-xyz", "chal")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "login.yotoplay.com"
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == ["client-123"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"] == ["state-xyz"]
    assert qs["redirect_uri"][0].endswith("/api/yoto/callback")
    assert "user:content:manage" in qs["scope"][0]


@pytest.mark.asyncio
async def test_access_token_accepts_naive_sqlite_expiry() -> None:
    """SQLite retire le fuseau des DateTime : un token valide doit rester utilisable."""
    settings = Settings(
        id=1,
        yoto_client_id="client",
        yoto_access_token="access",
        yoto_refresh_token="refresh",
        yoto_token_expires_at=datetime.now() + timedelta(minutes=5),
    )

    async def commit() -> None:
        pass

    client = YotoClient(settings, commit)
    try:
        assert await client._access_token() == "access"
    finally:
        await client.close()
