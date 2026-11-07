"""One chat turn: stream the model's reply as events, and keep the result.

Events, in order:
- `text`     {"delta"}        prose for the chat, as it arrives
- `progress` {"html"}         the work in progress, at most about once a second
- `version`  Version          a new Version was created from the finished reply
- `error`    {"message"}      the reply broke the contract or the model failed; no Version
- `done`     {"text"}         the final chat text of the model's message
"""

import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from embeds.context import turn_context
from embeds.prompt import system_prompt
from embeds.reply import ReplyError, ReplyStream, parse_reply, prose_before_html
from embeds.store import Store, Version

PROGRESS_INTERVAL_SECONDS = 1.0
MODEL_UNAVAILABLE = "Sorry, I couldn't answer just now. Please try again."

ChatEvent = tuple[str, dict[str, Any] | Version]


async def chat_turn(
    store: Store, model: BaseChatModel, embed_id: str, content: str, embed_origin: str
) -> AsyncIterator[ChatEvent]:
    history = store.messages_of(embed_id)
    latest = store.latest_version(embed_id)
    messages = turn_context(system_prompt(embed_origin), history, latest, content)
    store.add_message(embed_id, "journalist", content)

    stream = ReplyStream()
    last_sent_at = 0.0
    last_sent: str | None = None
    try:
        async for chunk in model.astream(messages):
            if text := stream.feed(chunk.text):
                yield "text", {"delta": text}
            progress = stream.work_in_progress()
            now = time.monotonic()
            if progress and progress != last_sent and now - last_sent_at >= PROGRESS_INTERVAL_SECONDS:
                yield "progress", {"html": progress}
                last_sent, last_sent_at = progress, now
        reply = parse_reply(stream.raw)
    except ReplyError as exc:
        # Keep whatever the model said before the broken HTML, so the chat still reads well.
        failure = (str(exc), prose_before_html(stream.raw).strip() or str(exc))
    except Exception as exc:  # The provider failed: bad key, rate limit, network, ...
        failure = (f"The model could not answer: {exc}", MODEL_UNAVAILABLE)
    else:
        version = store.add_version(embed_id, reply.html) if reply.html else None
        store.add_message(embed_id, "model", reply.text, version.number if version else None)
        if version:
            yield "version", version
        yield "done", {"text": reply.text}
        return

    error, text = failure
    store.add_message(embed_id, "model", text)
    yield "error", {"message": error}
    yield "done", {"text": text}
