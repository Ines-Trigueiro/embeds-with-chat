"""One chat turn: stream the model's reply as server-sent events, and keep the result.

Events, in order:
- `text`    {"delta"}          prose for the chat, as it arrives
- `draft`   {"html"}           the HTML so far, at most about once a second
- `version` {"number", ...}    a new Version was created from the finished reply
- `error`   {"message"}        the reply broke the contract or the model failed; no Version
- `done`    {"text"}           the final chat text of the model's message
"""

import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from embeds.prompt import system_prompt
from embeds.reply import ReplyError, ReplyStream, parse_reply
from embeds.store import Store, Version

DRAFT_INTERVAL_SECONDS = 1.0


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chat_turn(
    store: Store,
    model: BaseChatModel,
    embed_id: str,
    content: str,
    describe_version: Callable[[Version], dict[str, Any]],
) -> AsyncIterator[str]:
    store.add_message(embed_id, "journalist", content)
    messages = [SystemMessage(system_prompt()), HumanMessage(content)]

    stream = ReplyStream()
    last_draft_at = 0.0
    last_draft = None
    try:
        async for chunk in model.astream(messages):
            delta = chunk.text
            if text := stream.feed(delta):
                yield sse("text", {"delta": text})
            draft = stream.partial_html()
            now = time.monotonic()
            if draft and draft != last_draft and now - last_draft_at >= DRAFT_INTERVAL_SECONDS:
                yield sse("draft", {"html": draft})
                last_draft, last_draft_at = draft, now
    except Exception as exc:  # The provider failed: bad key, rate limit, network, ...
        message = f"The model could not answer: {exc}"
        store.add_message(embed_id, "model", message)
        yield sse("error", {"message": message})
        yield sse("done", {"text": message})
        return

    try:
        reply = parse_reply(stream.raw)
    except ReplyError as exc:
        text = parse_failure_text(stream.raw)
        store.add_message(embed_id, "model", text)
        yield sse("error", {"message": str(exc)})
        yield sse("done", {"text": text})
        return

    version = store.add_version(embed_id, reply.html) if reply.html else None
    store.add_message(embed_id, "model", reply.text, version.number if version else None)
    if version:
        yield sse("version", describe_version(version))
    yield sse("done", {"text": reply.text})


def parse_failure_text(raw: str) -> str:
    """The prose of a broken reply, so the chat still shows what the model said."""
    return ReplyStream().feed(raw) or raw[:200]
