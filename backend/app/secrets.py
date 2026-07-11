"""Chiffrement applicatif des secrets conservés dans SQLite.

SQLite n'offre aucun chiffrement de colonne. Les valeurs sensibles sont donc
chiffrées avant d'être persistées lorsque ``YOTO_SECRETS_KEY`` est configurée.
Les anciennes installations qui contiennent encore des valeurs en clair restent
lisibles et sont chiffrées lors de leur prochaine écriture.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import get_config

_PREFIX = "enc:v1:"


class SecretConfigurationError(RuntimeError):
    """Le secret de chiffrement est absent ou ne permet pas de déchiffrer."""


def _fernet() -> Fernet | None:
    configured = get_config().secrets_key.strip()
    if not configured:
        return None
    # Accepte une clé Fernet native ou une phrase secrète quelconque (dérivée
    # de façon déterministe pour faciliter la génération avec `openssl`).
    try:
        raw = base64.urlsafe_b64decode(configured.encode())
        if len(raw) == 32:
            return Fernet(configured.encode())
    except Exception:  # noqa: BLE001 - on retombe sur la dérivation ci-dessous
        pass
    digest = hashlib.sha256(configured.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str | None) -> str | None:
    if value is None or value.startswith(_PREFIX):
        return value
    fernet = _fernet()
    if fernet is None:
        return value
    return _PREFIX + fernet.encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    if value is None or not value.startswith(_PREFIX):
        return value
    fernet = _fernet()
    if fernet is None:
        raise SecretConfigurationError(
            "YOTO_SECRETS_KEY est nécessaire pour lire les secrets chiffrés"
        )
    try:
        return fernet.decrypt(value[len(_PREFIX) :].encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise SecretConfigurationError(
            "YOTO_SECRETS_KEY est invalide ou ne correspond pas à cette base"
        ) from exc


def is_set(value: str | None) -> bool:
    """Teste un secret sans exposer sa valeur ni considérer un texte vide."""
    return bool(decrypt(value))
