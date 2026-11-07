"""Signed preview URLs: how the journalist sees Versions that aren't published (ADR 0003).

Readers can only reach published versions. The editor preview still loads every
Version from the embed origin, under the same sandbox and CSP, through a URL
signed with a secret both origins share. Without the signature it is a 404.
"""

import hashlib
import hmac
import os
import secrets
from pathlib import Path


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


class PreviewSigner:
    def __init__(self, secret: bytes) -> None:
        self._secret = secret

    def sign(self, embed_id: str, number: int) -> str:
        message = f"{embed_id}:{number}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()[:32]

    def verify(self, embed_id: str, number: int, signature: str) -> bool:
        return hmac.compare_digest(self.sign(embed_id, number), signature)
