"""The contract for model replies: free text with at most one ```html block.

`parse_reply` judges a finished reply. `ReplyStream` splits a reply while it
streams, so the chat shows only the prose and the preview gets the work in progress.
"""

import re
from dataclasses import dataclass


class ReplyError(Exception):
    """The reply broke the contract; no Version may be created from it."""


@dataclass(frozen=True)
class Reply:
    text: str  # What the journalist sees in the chat: the reply without the HTML block.
    html: str | None


_OPENING_FENCE = re.compile(r"```html[^\S\n]*\n", re.IGNORECASE)
_CLOSING_FENCE = "\n```"
_PARTIAL_OPENING_FENCE = "```html\n"
_COMPLETE_DOCUMENT = re.compile(
    r"^\s*(<!doctype html[^>]*>\s*)?<html[\s>].*</html>\s*$", re.IGNORECASE | re.DOTALL
)


@dataclass(frozen=True)
class _Block:
    start: int  # Where the opening fence starts.
    body_start: int  # Where the HTML starts, just after the opening fence.
    body_end: int | None  # Where the HTML ends (before the closing fence), if it is closed.

    @property
    def after(self) -> int | None:
        """Where the prose after the closing fence starts, if the block is closed."""
        return None if self.body_end is None else self.body_end + len(_CLOSING_FENCE)


def _find_blocks(raw: str) -> list[_Block]:
    blocks = []
    for opening in _OPENING_FENCE.finditer(raw):
        # Search from the newline that ends the opening fence, so an empty block still closes.
        close_at = raw.find(_CLOSING_FENCE, opening.end() - 1)
        blocks.append(_Block(opening.start(), opening.end(), None if close_at == -1 else close_at))
    return blocks


def parse_reply(raw: str) -> Reply:
    blocks = _find_blocks(raw)
    if not blocks:
        return Reply(text=raw.strip(), html=None)
    if len(blocks) > 1:
        raise ReplyError("The model returned more than one HTML document.")

    [block] = blocks
    if block.body_end is None or block.after is None:
        raise ReplyError("The model's HTML was cut off before it was finished.")

    html = raw[block.body_start : block.body_end].strip()
    if not _COMPLETE_DOCUMENT.match(html):
        raise ReplyError("The model's HTML is not a complete document.")

    text = (raw[: block.start] + raw[block.after :]).strip()
    return Reply(text=text, html=html)


def prose_before_html(raw: str) -> str:
    """The prose up to the HTML block (or all of it), never a half-arrived fence."""
    blocks = _find_blocks(raw)
    if blocks:
        return raw[: blocks[0].start]
    # Hold back a trailing partial fence ("`", "``h", ...) until we know what it is.
    for keep in range(min(len(_PARTIAL_OPENING_FENCE), len(raw)), 0, -1):
        if _PARTIAL_OPENING_FENCE.startswith(raw[-keep:].lower()):
            return raw[:-keep]
    return raw


class ReplyStream:
    """Incrementally separates chat prose from the HTML block of a streaming reply."""

    def __init__(self) -> None:
        self.raw = ""
        self._prose_sent = 0

    def feed(self, delta: str) -> str:
        """Add a chunk; return any new prose that is now safe to show."""
        self.raw += delta
        prose = prose_before_html(self.raw)
        new = prose[self._prose_sent :]
        self._prose_sent = len(prose)
        return new

    def work_in_progress(self) -> str | None:
        """The HTML written so far, or None before the block starts."""
        blocks = _find_blocks(self.raw)
        if not blocks:
            return None
        block = blocks[0]
        return self.raw[block.body_start : block.body_end]
