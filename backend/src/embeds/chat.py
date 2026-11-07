"""One chat turn: stream the model's reply as events, and keep the result.

Events, in order:
- `guide`    {"name"}         the model is reading a guide (zero or more)
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
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage

from embeds.context import turn_context
from embeds.guides import LOAD_GUIDE_TOOL, base_guide, load_guide
from embeds.reply import ReplyError, ReplyStream, parse_reply, prose_before_html
from embeds.store import Store, Version

PROGRESS_INTERVAL_SECONDS = 1.0
MAX_GUIDE_ROUNDS = 3
MODEL_UNAVAILABLE = "Sorry, I couldn't answer just now. Please try again."

ChatEvent = tuple[str, dict[str, Any] | Version]


async def chat_turn(
    store: Store, model: BaseChatModel, embed_id: str, content: str, embed_origin: str
) -> AsyncIterator[ChatEvent]:
    history = store.messages_of(embed_id)
    latest = store.latest_version(embed_id)
    messages = turn_context(base_guide(embed_origin), history, latest, content)
    store.add_message(embed_id, "journalist", content)

    stream = ReplyStream()
    try:
        async for event in _stream_reply(model, messages, stream):
            yield event
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


async def _stream_reply(
    model: BaseChatModel, messages: list[BaseMessage], stream: ReplyStream
) -> AsyncIterator[ChatEvent]:
    """Stream rounds until the model answers instead of asking for guides."""
    with_guides = model.bind_tools([LOAD_GUIDE_TOOL])
    last_sent_at = 0.0
    last_sent: str | None = None

    for _ in range(MAX_GUIDE_ROUNDS + 1):
        gathered: AIMessageChunk | None = None
        async for chunk in with_guides.astream(messages):
            assert isinstance(chunk, AIMessageChunk)
            gathered = chunk if gathered is None else gathered + chunk
            if text := stream.feed(chunk.text):
                yield "text", {"delta": text}
            progress = stream.work_in_progress()
            now = time.monotonic()
            if progress and progress != last_sent and now - last_sent_at >= PROGRESS_INTERVAL_SECONDS:
                yield "progress", {"html": progress}
                last_sent, last_sent_at = progress, now

        if gathered is None or not gathered.tool_calls:
            return
        messages.append(AIMessage(content=gathered.text, tool_calls=gathered.tool_calls))
        for call in gathered.tool_calls:
            name = call["args"].get("name")
            yield "guide", {"name": name}
            messages.append(ToolMessage(content=load_guide(name), tool_call_id=call["id"] or ""))

    raise ReplyError("The model kept looking up guides without answering.")
