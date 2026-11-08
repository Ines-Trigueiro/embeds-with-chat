"""The streaming loop of a turn: the model's reply as chat events, filled into a `Reply`.

Guide rounds, text deltas, the Work in progress and parsing the finished reply. It records
nothing: what a turn leaves behind is up to `embeds.turns`.
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage

from embeds.datasets import DatasetAttachment, inject_datasets
from embeds.guides import LOAD_GUIDE_TOOL, load_guide
from embeds.languages import Language, with_document_language
from embeds.reply import ReplyError, ReplyStream, parse_reply, prose_before_html
from embeds.store import Version

PROGRESS_INTERVAL_SECONDS = 1.0
MAX_GUIDE_ROUNDS = 3
MODEL_UNAVAILABLE = "Sorry, I couldn't answer just now. Please try again."

ChatEvent = tuple[str, dict[str, Any] | Version]


@dataclass(frozen=True)
class Request:
    """One turn's request to the model, and what its reply needs to become a Version."""

    messages: list[BaseMessage]
    datasets: list[DatasetAttachment]
    embed_language: Language


@dataclass
class Reply:
    """What the model answered, filled in by `model_reply` as it streams."""

    text: str = ""
    html: str | None = None  # The finished document, with datasets and language applied.
    guides: list[str] = field(default_factory=list)  # Kept, so the chat shows them after a reload.
    error: str | None = None  # The reply broke the contract or the model failed: no html.


async def model_reply(
    model: BaseChatModel, request: Request, reply: Reply
) -> AsyncIterator[ChatEvent]:
    """Stream the reply's events into the chat while filling in `reply`. Stores nothing."""
    stream = ReplyStream()
    try:
        async for event in _stream_reply(model, request.messages, stream):
            if event[0] == "guide" and isinstance(event[1], dict):
                reply.guides.append(str(event[1]["name"]))
            yield event
        parsed = parse_reply(stream.raw)
        if parsed.html:
            # The figures go in here, from the file: never through the model (ADR 0002).
            injected = inject_datasets(parsed.html, request.datasets)
            reply.html = with_document_language(injected, request.embed_language)
        reply.text = parsed.text
    except ReplyError as exc:
        # Keep whatever the model said before the broken HTML, so the chat still reads well.
        reply.error, reply.text = str(exc), prose_before_html(stream.raw).strip() or str(exc)
    except Exception as exc:  # The provider failed: bad key, rate limit, network, ...
        reply.error, reply.text = f"The model could not answer: {exc}", MODEL_UNAVAILABLE


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
