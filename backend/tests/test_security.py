"""Régressions sur le stockage des secrets et les tokens de streaming."""

from __future__ import annotations

import pytest

import app.secrets as secrets_module
from app.secrets import SecretConfigurationError, decrypt, encrypt


class _Config:
    secrets_key = "a" * 64


def test_secrets_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets_module, "get_config", lambda: _Config())

    stored = encrypt("navidrome-password")

    assert stored is not None
    assert stored.startswith("enc:v1:")
    assert "navidrome-password" not in stored
    assert decrypt(stored) == "navidrome-password"


def test_plaintext_values_remain_backward_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets_module, "get_config", lambda: _Config())
    assert decrypt("legacy-token") == "legacy-token"


def test_encrypted_values_fail_closed_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets_module, "get_config", lambda: _Config())
    stored = encrypt("secret")
    monkeypatch.setattr(secrets_module, "get_config", lambda: type("C", (), {"secrets_key": ""})())

    with pytest.raises(SecretConfigurationError):
        decrypt(stored)
