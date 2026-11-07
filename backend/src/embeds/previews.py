"""Signed, expiring preview URLs: how the journalist sees versions that aren't published.

Readers can only reach published versions (ADR 0003). The editor preview still loads
every Version from the embed origin, under the same sandbox and CSP, through a URL
signed with a secret both origins share. The signature covers the expiry, so a
preview URL that leaks stops working; without a valid signature it is a 404.
"""

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from embeds.config import Settings


def load_or_create_secret(data_dir: Path) -> bytes:
    """Both origins read the same file on the shared data volume; the first to start creates it."""
    path = data_dir / "preview-secret"
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes()
    with os.fdopen(fd, "wb") as f:
        secret = secrets.token_bytes(32)
        f.write(secret)
    return secret


class Previews:
    def __init__(self, secret: bytes, embed_origin: str, ttl_seconds: int) -> None:
        self._secret = secret
        self._embed_origin = embed_origin
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "Previews":
        secret = load_or_create_secret(settings.data_dir)
        return cls(secret, settings.embed_origin, settings.preview_ttl_seconds)

    def url(self, embed_id: str, number: int) -> str:
        expires = int(time.time()) + self._ttl_seconds
        sig = self._sign(embed_id, number, expires)
        return f"{self._embed_origin}/preview/{embed_id}/{number}?exp={expires}&sig={sig}"

    def is_valid(self, embed_id: str, number: int, expires: int, sig: str) -> bool:
        authentic = hmac.compare_digest(self._sign(embed_id, number, expires), sig)
        return authentic and time.time() < expires

    def _sign(self, embed_id: str, number: int, expires: int) -> str:
        message = f"{embed_id}:{number}:{expires}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()[:32]
