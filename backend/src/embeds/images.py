"""Image attachments: served from the embed origin, and shown to the model as vision input.

The type comes from the file's own bytes, never its name, and only raster formats are
accepted: an SVG can carry scripts, and the embed origin must never serve one as an image.
"""

from dataclasses import dataclass

MAX_IMAGES_FOR_MODEL = 5  # The most recent ones; each costs the model's attention and tokens.

_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def image_type(content: bytes) -> str | None:
    """The image's media type, from its first bytes; None if it isn't an accepted image."""
    for signature, media_type in _SIGNATURES:
        if content.startswith(signature):
            return media_type
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def image_url(embed_origin: str, embed_id: str, attachment_id: str) -> str:
    return f"{embed_origin}/attachments/{embed_id}/{attachment_id}"


@dataclass(frozen=True)
class ImageForModel:
    name: str
    url: str
    media_type: str
    content: bytes
