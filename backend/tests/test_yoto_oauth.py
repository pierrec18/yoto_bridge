"""Tests du flux OAuth PKCE Yoto."""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from app.yoto import oauth


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
