"""The contract for model replies: free text with at most one ```html block.

`parse_reply` judges a finished reply. `ReplyStream` splits a reply while it
streams, so the chat shows only the prose and the preview gets the HTML.
"""

import re
from dataclasses import dataclass

OPEN_FENCE = "```html"
CLOSE_FENCE = "```"


class ReplyError(Exception):
    """The reply broke the contract; no Version may be created from it."""


@dataclass(frozen=True)
class Reply:
    text: str  # What the journalist sees in the chat: the reply without the HTML block.
    html: str | None


_OPEN = re.compile(r"```html[^\S\n]*\n", re.IGNORECASE)
_DOCUMENT = re.compile(r"^\s*(<!doctype html[^>]*>\s*)?<html[\s>].*</html>\s*$", re.IGNORECASE | re.DOTALL)


def parse_reply(raw: str) -> Reply:
    blocks = list(_OPEN.finditer(raw))
    if not blocks:
        return Reply(text=raw.strip(), html=None)
    if len(blocks) > 1:
        raise ReplyError("The model returned more than one HTML document.")

    opening = blocks[0]
    close_at = raw.find("\n" + CLOSE_FENCE, opening.end() - 1)
    if close_at == -1:
        raise ReplyError("The model's HTML was cut off before it was finished.")

    html = raw[opening.end() : close_at + 1].strip()
    if not _DOCUMENT.match(html):
        raise ReplyError("The model's HTML is not a complete document.")

    after = raw[close_at + 1 + len(CLOSE_FENCE) :]
    text = (raw[: opening.start()] + after).strip()
    return Reply(text=text, html=html)


class ReplyStream:
    """Incrementally separates chat prose from the HTML block of a streaming reply."""

    def __init__(self) -> None:
        self.raw = ""
        self._text_sent = 0

    def feed(self, delta: str) -> str:
        """Add a chunk; return any new prose that is now safe to show."""
        self.raw += delta
        visible = self._visible_text()
        new = visible[self._text_sent :]
        self._text_sent = len(visible)
        return new

    def partial_html(self) -> str | None:
        """The HTML written so far, or None before the block starts."""
        opening = _OPEN.search(self.raw)
        if not opening:
            return None
        body = self.raw[opening.end() :]
        close_at = body.find("\n" + CLOSE_FENCE)
        return body if close_at == -1 else body[: close_at + 1]

    def _visible_text(self) -> str:
        opening = _OPEN.search(self.raw)
        if opening:
            return self.raw[: opening.start()]
        # Hold back a trailing partial fence ("`", "``h", ...) until we know what it is.
        for keep in range(min(len(OPEN_FENCE) + 1, len(self.raw)), 0, -1):
            tail = self.raw[-keep:]
            if (OPEN_FENCE + "\n").startswith(tail.lower()):
                return self.raw[:-keep]
        return self.raw
